from dataclasses import replace
from .concepts import BY_NAME, DERIVED, Metric
from .engine import reconstruct, fiscal_periods, derive
from .sec import SECError, company_facts, filing_url, parse_inline, verify


class Research:
    def __init__(self, client, company, submissions, history=False):
        self.client = client
        self.company = company
        self.submissions = submissions
        self.filings = client.filings(submissions, history)
        self.facts = company_facts(company, self.filings)
        self.documents = {}
        self.log = list(client.history_errors)
        self.additional_version_scans = 0

    def inspect_filing(self, filing):
        acc=filing['accessionNumber']
        if acc in self.documents:
            return
        url=filing_url(self.company['cik'],filing)
        try:
            parsed,text=parse_inline(self.client.get(url,ttl=30*86400),self.company['cik'],filing,url)
            self.documents[acc]=(parsed,text)
            self.facts=[verify(f,parsed) if f.accession==acc else f for f in self.facts]
            existing={(f.concept,f.start,f.end,f.unit,f.value,f.accession,f.dimensions) for f in self.facts}
            self.facts.extend(f for f in parsed if (f.concept,f.start,f.end,f.unit,f.value,f.accession,f.dimensions) not in existing)
            self.log.append({'accession':acc,'url':url,'status':'Document inspected','inline_facts':len(parsed),
                             'search_scope':'Primary filing, embedded notes and comparative-version precision'})
        except SECError as exc:
            self.log.append({'accession':acc,'url':url,'status':'Filing verification unavailable','error':str(exc)})

    def investigate(self, year, max_filings=12):
        periods = self.periods(year)
        start = periods[0] if periods else f'{year-1}-01-01'
        end = periods[1][4] if periods else f'{year}-12-31'
        relevant = [f for f in self.filings if f['form'] in ('10-K', '10-Q', '10-K/A', '10-Q/A')
                    and start <= f.get('reportDate', '') <= end]
        relevant.sort(key=lambda f: (f.get('reportDate', ''), f['filingDate']))
        for filing in relevant[:max_filings]:
            self.inspect_filing(filing)
        if len(relevant) > max_filings:
            self.log.append({'status': 'Incomplete scope', 'remaining_filings': len(relevant) - max_filings})

    def periods(self, year):
        # Use one well-defined consolidated income concept to avoid mixing calendar changes.
        best = None
        for tag in ('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'NetIncomeLoss',
                    'NetCashProvidedByUsedInOperatingActivities'):
            periods = fiscal_periods([f for f in self.facts if f.concept == 'us-gaap:' + tag and not f.dimensions], year)
            if periods and (best is None or len(periods[1]) > len(best[1])):
                best = periods
        return best

    def investigate_concept(self, name):
        if name not in BY_NAME:
            return
        for tag in BY_NAME[name].tags:
            try:
                payload=self.client.concept(self.company['cik'],'us-gaap',tag)
                wrapped={'cik':self.company['cik'],'facts':{'us-gaap':{tag:{'label':payload.get('label',tag),'units':payload['units']}}}}
                incoming=company_facts(wrapped,self.filings)
                for accession,(parsed,text) in self.documents.items():
                    incoming=[verify(f,parsed) if f.accession==accession else f for f in incoming]
                known={f.id for f in self.facts}
                self.facts.extend(f for f in incoming if f.id not in known)
                self.log.append({'status':'CompanyConcept inspected','concept':'us-gaap:'+tag,'observations':len(incoming)})
            except SECError as exc:
                self.log.append({'status':'Filing verification unavailable','scope':'CompanyConcept','concept':tag,'error':str(exc)})

    def cell(self, name, year, q, custom=None):
        if name in DERIVED:
            spec = DERIVED[name]
            names, ops = list(spec[:2]), [spec[2]]
            if len(spec) > 3:
                names.append(spec[3]); ops.append(spec[4])
            result = derive(self.company['entityName'], self.submissions.get('tickers', [''])[0], name,
                            [self.cell(n, year, q) for n in names], ops)
        else:
            metric = BY_NAME.get(name) or Metric(name, 'Custom', custom.get('kind','nonadditive'), (), (), custom['unit'])
            result = reconstruct(self.company['entityName'], self.submissions.get('tickers', [''])[0],
                                 metric, self.facts, year, q, self.periods(year), custom['concept'] if custom else None,
                                 tuple(custom.get('dimensions',())) if custom else ())
            if result.status=='Ambiguous or conflicting':
                # CompanyFacts omits decimals. Inspect comparative versions before treating
                # a change in disclosed rounding precision as a financial restatement.
                accessions={f.accession for f in result.inputs if not f.verified}
                for accession in accessions:
                    if self.additional_version_scans>=8:
                        break
                    filing=next((f for f in self.filings if f['accessionNumber']==accession),None)
                    if filing and accession not in self.documents:
                        self.additional_version_scans+=1
                        self.inspect_filing(filing)
                result=reconstruct(self.company['entityName'],self.submissions.get('tickers',[''])[0],
                    metric,self.facts,year,q,self.periods(year),custom['concept'] if custom else None,
                    tuple(custom.get('dimensions',())) if custom else ())
            if custom:
                result.reasoning.append('Exact concept and dimensional scope explicitly selected by analyst; no equivalence to a standard metric is asserted.')
                result.warnings.append('Custom and segment reporting definitions and reorganizations require analyst review.')
        result.investigation = list(self.log)
        if result.value is None and any(x['status'] in ('Filing verification unavailable', 'Incomplete scope') for x in self.log):
            result.status = 'Filing verification unavailable'
        if result.value is not None and not result.verified:
            result.warnings.append('Original filing context not matched; this value is not verified.')
        return result

    def classify_disclosure(self, cell, accession, quote, status, rationale):
        """Attach an explicit analyst conclusion only to a literal retrieved disclosure."""
        if status not in ('Not applicable','Not separately disclosed'):
            raise ValueError('Unsupported qualitative classification')
        if cell.value is not None:
            raise ValueError('A quantitative value cannot be replaced by a qualitative annotation')
        if accession not in self.documents or not quote.strip() or len(quote.strip()) < 20:
            raise ValueError('Select a retrieved filing and an exact supporting passage of at least 20 characters')
        if quote not in self.documents[accession][1] or not rationale.strip():
            raise ValueError('The exact quote must occur in the retrieved filing and an analyst rationale is required')
        filing=next(f for f in self.filings if f['accessionNumber']==accession)
        cell.status=status
        cell.disclosure_evidence=[{'accession':accession,'url':filing_url(self.company['cik'],filing),
                                  'quote':quote,'rationale':rationale,'source_matched':True,
                                  'classification_basis':'Explicit analyst review; semantic conclusion not automated'}]
        cell.warnings.append('Analyst-selected classification. Literal passage matched; conclusion and requested-period applicability require review.')
        return cell
