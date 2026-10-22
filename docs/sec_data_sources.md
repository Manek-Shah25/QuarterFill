# SEC data sources and coverage

- Company index: https://www.sec.gov/files/company_tickers.json
- CompanyFacts: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json
- Submissions: https://data.sec.gov/submissions/CIK##########.json and older files
- Actual primary documents: paths assembled only from returned accession and document names
- SEC API documentation: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Fair access: https://www.sec.gov/about/developer-resources

One request controller enforces a process-wide 4 requests/second ceiling, retries rate
limits, caches responses and exposes failures. Configure a real operator contact email.
Multiple app replicas are not coordinated; keep the free deployment to a single instance.

The investigator inspects up to 12 relevant primary filings per requested year, including
embedded tables and footnotes and supported inline numeric facts. It retains context
excerpts and extension/segment facts for manual inspection. Historical submissions are
loaded when selected. Exhaustion of the scan budget is reported as incomplete.

The Missing Data Investigator also provides explicit CompanyConcept API investigation.
Custom and segment disclosure contexts can be selected in the Filing Explorer; additive
handling requires an explicit analyst choice and keeps the selected dimensional scope.
Qualitative not-applicable/not-separately-disclosed decisions can be recorded only with
a literal retrieved passage and an analyst rationale; semantic conclusions remain analyst work.
Offline SEC TSV data sets can be uploaded for joined disclosure-row inspection; they are
not automatically transformed into context-verified financial cells.

Not yet implemented: external exhibit/schedule crawling,
raw XBRL instance and linkbase parsing, automated definition verification for custom tags,
automatic period reconstruction from SEC Financial Statement and Notes Data Sets, untagged table numeric recovery,
and semantic not-applicable/not-separately-disclosed classification.

Snapshots use exact SEC response envelopes with official URL, retrieval timestamp and
body checksum. The checksum detects corruption; it does not independently authenticate
an untrusted mirror. Use only an operator-controlled repository populated by the included
refresh script. Snapshots display their retrieval time and are never presented as live.
