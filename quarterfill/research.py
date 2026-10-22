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

    def investigate(self, year, max_filings=12):
        periods = self.periods(year)
        start = periods[0] if periods else f'{year-1}-01-01'
        end = periods[1][4] if periods else f'{year}-12-31'
        relevant = [f for f in self.filings if f['form'] in ('10-K', '10-Q', '10-K/A', '10-Q/A')
                    and start <= f.get('reportDate', '') <= end]
        relevant.sort(key=lambda f: (f.get('reportDate', ''), f['filingDate']))
        for filing in relevant[:max_filings]:
            acc = filing['accessionNumber']
            if acc in self.documents:
                continue
            url = filing_url(self.company['cik'], filing)
            try:
                parsed, text = parse_inline(self.client.get(url, ttl=30*86400), self.company['cik'], filing, url)
                self.documents[acc] = (parsed, text)
                self.facts = [verify(f, parsed) if f.accession == acc else f for f in self.facts]
                existing = {(f.concept, f.start, f.end, f.unit, f.value, f.accession, f.dimensions) for f in self.facts}
                self.facts.extend(f for f in parsed if (f.concept, f.start, f.end, f.unit, f.value, f.accession, f.dimensions) not in existing)
                self.log.append({'accession': acc, 'url': url, 'status': 'Document inspected',
                                 'inline_facts': len(parsed), 'search_scope': 'Primary filing including embedded financial notes'})
            except SECError as exc:
                self.log.append({'accession': acc, 'url': url, 'status': 'Filing verification unavailable', 'error': str(exc)})
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

    def cell(self, name, year, q, custom=None):
        if name in DERIVED:
            spec = DERIVED[name]
            names, ops = list(spec[:2]), [spec[2]]
            if len(spec) > 3:
                names.append(spec[3]); ops.append(spec[4])
            result = derive(self.company['entityName'], self.submissions.get('tickers', [''])[0], name,
                            [self.cell(n, year, q) for n in names], ops)
        else:
            metric = BY_NAME.get(name) or Metric(name, 'Custom', 'nonadditive', (), (), custom['unit'])
            result = reconstruct(self.company['entityName'], self.submissions.get('tickers', [''])[0],
                                 metric, self.facts, year, q, self.periods(year), custom['concept'] if custom else None)
        result.investigation = list(self.log)
        if result.value is None and any(x['status'] in ('Filing verification unavailable', 'Incomplete scope') for x in self.log):
            result.status = 'Filing verification unavailable'
        if result.value is not None and not result.verified:
            result.warnings.append('Original filing context not matched; this value is not verified.')
        return result
