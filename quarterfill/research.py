from dataclasses import replace
from .concepts import BY_NAME, DERIVED, METRICS, Metric
from .engine import reconstruct, fiscal_periods, derive
from .sec import SECError, company_facts, filing_url, parse_inline, verify
from .cash import cash_balance, CASH_TAGS
from .formulas import recover, financial_industry
from .taxonomy import load_taxonomy, custom_candidates, normalized
from .filing_tables import parse_tables
from datetime import date, timedelta
from .revenue_math import RevenueMath


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
        self.taxonomies = {}
        self.html_documents = {}
        self.version_policy = 'strict'
        self._cell_cache = {}
        self._interval_cache = {}

    def inspect_filing(self, filing):
        acc=filing['accessionNumber']
        if acc in self.documents:
            return
        url=filing_url(self.company['cik'],filing)
        try:
            html=self.client.get(url,ttl=30*86400)
            parsed,text=parse_inline(html,self.company['cik'],filing,url)
            self.html_documents[acc]=html
            try:
                parsed.extend(parse_tables(html,self.company['cik'],filing,url,METRICS,parsed))
            except SECError as exc:
                self.log.append({'accession':acc,'status':'Incomplete scope','scope':'Untagged filing tables','error':str(exc)})
            self.documents[acc]=(parsed,text)
            self.facts=[verify(f,parsed) if f.accession==acc else f for f in self.facts]
            existing={(f.concept,f.start,f.end,f.unit,f.value,f.accession,f.dimensions,f.table) for f in self.facts}
            self.facts.extend(f for f in parsed if (f.concept,f.start,f.end,f.unit,f.value,f.accession,f.dimensions,f.table) not in existing)
            self.log.append({'accession':acc,'url':url,'status':'Document inspected','inline_facts':len(parsed),
                             'search_scope':'Primary filing, embedded notes and comparative-version precision'})
        except SECError as exc:
            self.log.append({'accession':acc,'url':url,'status':'Filing verification unavailable','error':str(exc)})

    def investigate(self, year, max_filings=12):
        periods = self.periods(year)
        start = periods[0] if periods else f'{year-1}-01-01'
        end = periods[1].get(4,periods[1].get(0)) if periods else f'{year}-12-31'
        relevant = [f for f in self.filings if f['form'] in ('10-K', '10-Q', '10-K/A', '10-Q/A', '10-KT', '10-KT/A', '10-QT', '10-QT/A')
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
        for tag in (CASH_TAGS if name == 'Cash' else BY_NAME[name].tags):
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

    def selected_facts(self):
        if self.version_policy=='strict':
            return self.facts
        # Choose one disclosure version for each exact concept/context/period/unit.
        grouped={}
        for f in self.facts:
            key=(f.concept,f.start,f.end,f.unit,f.dimensions)
            if key not in grouped or ((f.filed<grouped[key].filed) if self.version_policy=='original' else (f.filed>grouped[key].filed)):
                grouped[key]=f
        selected={(k,f.accession) for k,f in grouped.items()}
        return [f for f in self.facts if ((f.concept,f.start,f.end,f.unit,f.dimensions),f.accession) in selected]

    def fallback(self,metric,year,q):
        # Target only reports already selected for this fiscal year. Lazy once per report.
        relevant=[f for f in self.filings if f['accessionNumber'] in self.documents]
        calendar=self.periods(year)
        if calendar:
            start,ends=calendar
            end=ends.get(4,ends.get(0))
            relevant=[f for f in relevant if start<=f.get('reportDate','')<=end]
        relevant.sort(key=lambda f:(f.get('reportDate',''),f['filingDate']),reverse=True)
        for filing in relevant[:4]:
            acc=filing['accessionNumber']
            if acc not in self.taxonomies:
                self.taxonomies[acc]=load_taxonomy(self.client,self.html_documents[acc],filing_url(self.company['cik'],filing))
                self.log.append({'status':'Extension taxonomy inspected','accession':acc,
                                 'documents':len(self.taxonomies[acc].documents),'errors':self.taxonomies[acc].errors})
        facts=self.selected_facts()
        candidates=[]
        for acc,taxonomy in self.taxonomies.items():
            candidates.extend(custom_candidates(metric,taxonomy,[f for f in facts if f.accession==acc]))
        candidates.extend(f for f in facts if f.concept=='html:'+normalized(metric.name))
        if not candidates:
            return None
        # Reconstruct each supported concept separately; differing custom candidates conflict.
        results=[reconstruct(self.company['entityName'],self.submissions.get('tickers',[''])[0],metric,candidates,
                    year,q,self.periods(year),concept) for concept in sorted({f.concept for f in candidates},key=lambda c:(c.startswith('html:'),c))]
        values=[r for r in results if r.value is not None or r.status=='Ambiguous or conflicting']
        if not values:
            return None
        first=values[0]
        if any(r.value!=first.value for r in values):
            first.value=None; first.status='Ambiguous or conflicting'
            first.inputs=[f for r in values for f in r.inputs]
            first.warnings.append('Supported filing-specific interpretations disagree.')
        else:
            first.reasoning.append('Recovered from a matching original filing disclosure with confirmed accounting context.')
        return first

    def cell(self, name, year, q, custom=None, _seen=None):
        seen=set(_seen or ()) | {name}
        cache_key=(name,year,q,self.version_policy,len(self.facts),len(self.documents))
        if _seen is None and not custom and cache_key in self._cell_cache:
            return self._cell_cache[cache_key]
        if name in DERIVED:
            spec = DERIVED[name]
            names, ops = list(spec[:2]), [spec[2]]
            if len(spec) > 3:
                names.append(spec[3]); ops.append(spec[4])
            result = derive(self.company['entityName'], self.submissions.get('tickers', [''])[0], name,
                            [self.cell(n, year, q) for n in names], ops)
            if name=='Free cash flow' and result.components and result.components[1].value<0:
                result.value=None; result.status='Ambiguous or conflicting'
                result.warnings.append('Capital expenditures must be a positive outflow for this formula. Check the reported sign.')
        else:
            if name not in BY_NAME and not custom:
                raise ValueError(f'Unknown financial metric: {name}')
            metric = BY_NAME.get(name) or Metric(name, 'Custom', custom.get('kind','nonadditive'), (), (), custom['unit'])
            metric_facts=self.selected_facts()
            if name=='Operating depreciation and amortization':
                income_tables={(f.table,f.accession,f.start,f.end) for f in metric_facts if f.table and f.concept=='us-gaap:OperatingIncomeLoss'}
                metric_facts=[f for f in metric_facts if (f.table,f.accession,f.start,f.end) in income_tables]
            if name=='Beginning cash including restricted cash':
                calendar=self.periods(year)
                anchor=calendar[0] if calendar and q in (0,1) else (calendar[1].get(q-1) if calendar else None)
                target=(date.fromisoformat(anchor)-timedelta(days=1)).isoformat() if anchor and q in (0,1) else anchor
                result=reconstruct(self.company['entityName'],self.submissions.get('tickers',[''])[0],
                    replace(metric,kind='instant'),self.selected_facts(),year,1,(target,{1:target}) if target else None)
                result.year=year; result.quarter='FY' if q==0 else f'Q{q}'
                result.start=None
                result.reasoning.append('Beginning cash is the reported balance immediately before the period starts, including restricted cash.')
                return result
            result = reconstruct(self.company['entityName'], self.submissions.get('tickers', [''])[0],
                                 metric, metric_facts, year, q, self.periods(year), custom['concept'] if custom else None,
                                 tuple(custom.get('dimensions',())) if custom else ())
            if name=='Operating depreciation and amortization' and result.value is not None:
                # The same generic D&A tag is often used on the cash flow statement.
                # It is an income-statement expense only when that presentation is proven.
                sources=result.inputs
                if not all(any(f.table and other.table==f.table and other.accession==f.accession
                    and other.concept=='us-gaap:OperatingIncomeLoss' and other.start==f.start and other.end==f.end
                    for other in self.facts) for f in sources):
                    result.value=None; result.inputs=[]; result.status='Insufficient information'
                    result.reasoning.append('Depreciation is not confirmed as a separate income-statement line for this period.')
            if name == 'Cash' and not custom:
                result = cash_balance(self.company['entityName'],self.submissions.get('tickers',[''])[0],self.selected_facts(),year,q,self.periods(year))
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
                    metric,metric_facts if name=='Operating depreciation and amortization' else self.selected_facts(),year,q,self.periods(year),custom['concept'] if custom else None,
                    tuple(custom.get('dimensions',())) if custom else ())
                if name == 'Cash' and not custom:
                    result = cash_balance(self.company['entityName'],self.submissions.get('tickers',[''])[0],self.selected_facts(),year,q,self.periods(year))
            if not custom and result.value is None and result.status!='Ambiguous or conflicting':
                if metric.kind=='flow' and self.periods(year) and 4 in self.periods(year)[1]:
                    interval_key=(name,year,self.version_policy,len(self.facts))
                    if interval_key not in self._interval_cache:
                        candidates=[f for f in metric_facts if f.concept in {'us-gaap:'+t for t in metric.tags}
                                    and f.unit==metric.unit and not f.dimensions and f.verified]
                        self._interval_cache[interval_key]=RevenueMath(self,year,candidates,default_name=name)
                    model=self._interval_cache[interval_key]
                    possible=[model.cells('us-gaap:'+tag,(),name)[4 if q==0 else q-1] for tag in metric.tags]
                    known=[c for c in possible if c.value is not None or c.status=='Ambiguous or conflicting']
                    if known:
                        result=known[0]
                        if any(c.value!=result.value for c in known):
                            result.value=None; result.status='Ambiguous or conflicting'
                if result.value is None and result.status!='Ambiguous or conflicting':
                    result=self.fallback(metric,year,q) or result
                if result.value is None and result.status!='Ambiguous or conflicting':
                    result=recover(self,name,year,q,seen) or result
                if result.value is None:
                    result.reasoning.append('Checked equivalent concepts, original statement and note disclosures, supported extension definitions, and exact accounting formulas. No unique supported amount was established.')
                    if financial_industry(self.submissions) and name in ('Gross profit','Cost of revenue','Inventory'):
                        result.reasoning.append('This company uses financial-industry reporting. Industrial-company formulas have not been assumed; absence alone does not establish that an item is inapplicable.')
            if custom:
                result.reasoning.append('Exact concept and dimensional scope explicitly selected by analyst; no equivalence to a standard metric is asserted.')
                result.warnings.append('Custom and segment reporting definitions and reorganizations require analyst review.')
        result.investigation = list(self.log)
        if result.value is None and result.status!='Ambiguous or conflicting' and any(x['status'] in ('Filing verification unavailable', 'Incomplete scope') for x in self.log):
            result.status = 'Filing verification unavailable'
        if result.value is not None and not result.verified:
            result.warnings.append('Original filing context not matched; this value is not verified.')
        if _seen is None and not custom:
            self._cell_cache[(name,year,q,self.version_policy,len(self.facts),len(self.documents))]=result
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
