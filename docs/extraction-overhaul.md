# Financial extraction overhaul — October 23, 2026

The original pipeline used a narrow concept registry and exact period matching. It already read embedded Inline XBRL, including custom facts and notes, but could not establish the accounting meaning of most extensions. Its general calculation engine handled cumulative subtraction and a few named calculations. Most of the more complete interval and parent/child mathematics was limited to revenue segments. There were no general statement reconciliations. Several aggregates and components also shared a mapping despite different scopes.

## What changed

| Module | Responsibility |
|---|---|
| `concepts.py` | 107 entries: 26 income, 52 balance sheet, 29 cash flow. Definitions, primary/alternative tags, units, period types, applicability, exclusions, and formula access. |
| `sec.py` | Official SEC client, caching, retry/rate controls, Inline XBRL contexts and units; scale/sign provenance and bounded parsing. |
| `taxonomy.py` | Filing-local extension schemas, labels/documentation, presentation roles and calculation arcs. XML external entities and network resolution are disabled. |
| `filing_tables.py` | Untagged-table fallback using exact labels, explicit full dates, stated monetary scale and financial-statement context. |
| `research.py` | Recovery orchestration, retained filing text, original/latest/strict policies, lazy taxonomy inspection and memoized results. |
| `engine.py`, `revenue_math.py` | Exact fiscal dates, annual/quarter selection, cumulative subtraction and general interval recovery without crossing concepts, units or dimensions. |
| `formulas.py` | Central accounting identities, verified inputs, cycle prevention, statement/relationship guards and financial-industry restrictions. |
| `validation.py` | Configurable Decimal rounding checks, discrepancies, missing-input explanations and mezzanine equity treatment. |
| `models.py`, `export.py` | Five normalized accounting statuses, source/method/scale/definition/relationship provenance, recursive formulas and Excel source/quality sheets. |
| `app.py` | Existing pages plus annual/filter views, reported filing rows, source explanations, statement checks and a compact Excel download. |

Recovery checks standardized facts, verified equivalent concepts, filing-level custom definitions and presentation context, original table disclosures, compatible accounting formulas, and comparative reporting versions. Inspection is targeted and bounded; a failure is logged and does not turn a missing amount into zero. Embedded XBRL notes are read with the primary document. Primary structured facts retain priority over untagged fallback rows.

The extension reader uses the existing lxml stack rather than adding Arelle. It reads the relationships needed by this resolver; it is **not** a complete XBRL conformance validator. Custom mapping requires exact supported terminology, matching schema period and unit, a relevant statement role, and documentation supporting the standardized concept. A familiar keyword or calculation-child relationship alone never establishes equivalence. Unsupported custom facts remain visible as reported company lines without being relabeled as a standardized metric.

## Accounting safeguards

Gross and finished-goods inventory remain separate from net inventory. Combined receivables remain separate from trade accounts. Goodwill, finite-lived and indefinite-lived intangible assets remain separate. Broader productive-asset purchases do not replace PP&E CapEx. Aggregate D&A and PP&E-only D&A, and total and common-stock dividends, are separate rows. Income-statement D&A requires evidence of that statement presentation. Working-capital movements are not balance-sheet amounts. Rows are not automatically summed, so aggregates and components do not double-count.

The centralized formulas include:

- Revenue − gross profit = cost of revenue, and revenue − cost of revenue = gross profit, with matching reported table/period evidence and an industry guard.
- Assets − current assets = noncurrent assets; liabilities − current liabilities = noncurrent liabilities.
- Assets = liabilities + permanent consolidated equity + separately reported mezzanine interests. Residual formulas preserve reported redeemable interests rather than folding them into permanent equity.
- Gross PP&E − matching accumulated depreciation = net PP&E, requiring the same disclosed table and asset scope.
- Finite-lived plus indefinite-lived net intangible assets = total identifiable net intangibles; an absent component is never treated as zero.
- Operating cash flow − positive PP&E CapEx = free cash flow.
- Continuing-operations income plus tax = pretax income; gross profit minus operating expenses = operating income; and operating + investing + financing + exchange rates = cash change **only when the filing's complete calculation relationship proves the exact equation**. Extra or missing terms block the formula.
- Quarterly cumulative subtraction and any uniquely supported path between fiscal boundaries, such as full year − Q1 − Q3 − Q4 = Q2. Two known quarters alone do not establish the other two.

Reported numbers are never replaced merely to pass a check. Cash reconciliation requires FX evidence; missing FX is not assumed to be zero. Other cash adjustments can produce a review flag. Rounding tolerances sum disclosed source precision, with configurable absolute and relative floors. A check involving an amount calculated from the same identity is explicitly described as not independent.

Balance sheets use exact dates and are never differenced. EPS and weighted-average shares are never obtained by subtracting annual figures. Fiscal calendars use disclosed durations, including 52/53-week years. Explicit short 10-KT transition periods can be shown annually; they are not mislabeled Q4. Their standalone quarters remain unresolved without supported quarter boundaries. Fiscal-year labels follow the calendar year of the annual period end, as explained in each calculation.

The strict version policy retains conflicting filing versions. First/latest policies choose filing chronology separately for each exact concept, period, unit and dimensional context, retaining precision evidence within the selected accession. This is not a claim that all company reorganizations or retrospectively changed definitions can be reconciled automatically. Revenue-segment reporting has its separate reporting-year choice.

Reported, Derived, Unavailable, Not Applicable and Ambiguous are available in the audit model. Not Applicable requires positive disclosure and explicit classification; SIC or a missing tag alone does not assign it. Financial-industry SIC classification blocks industrial formulas, rather than forcing unsupported zeros.

## Recorded evidence

`tests/fixtures/overhaul_expected.json` contains fixed expectations transcribed after reading original filing rows and date columns. `data/validation/overhaul-review.json` preserves labels, exact dates, original filing URLs, context excerpts and numerical source facts. This was a source review by Codex, **not an independent human audit**.

| Company | FY2025 / year-end checks |
|---|---|
| AAPL | Inventory, revenue, cost of sales, PP&E CapEx |
| WMT | Inventory, cost of sales, accounts payable; additional note-only intangible-assets regression |
| MSFT | Current and noncurrent unearned revenue, finite-lived net intangible assets; broader custom acquisition scope is not mislabeled |
| ADBE | Deferred revenue, operating cash flow, stock compensation |
| UNH | Trade receivables, goodwill, identifiable intangible assets; balance check includes $1.608 billion redeemable interests |
| CAT | Inventory, net PP&E, D&A, PP&E CapEx excluding equipment leased to others, as the report labels it |
| JPM | Reported revenue, assets, liabilities, negative operating cash flow; industrial gross-profit formula is blocked |

`scripts/benchmark_overhaul.py` runs the old implementation at `c314c96569290ca976b448c00ae71f36c28845b1` and the revised implementation on the same authentic SEC inputs with the strict policy in both. **19/24 → 24/24** source-matched expected amounts; the denominator includes newly supported metrics. This is a coverage measurement for those selected cells, not an accuracy estimate for the entire SEC universe. The machine-readable results are in `data/validation/overhaul-benchmark.json`.

Synthetic tests independently cover custom definition safeguards, untagged notes, negatives/scales, exact-scope exclusions, cost recovery, interval underdetermination, original/restated policy, transitions and FX reconciliation. Existing tests continue to cover exact ticker identity, noncalendar dates, conflicting sources, revenue subgroups and cell-click explanations.

Local validation: **102 tests passed** in 187.64 seconds, with no warnings; the final untagged-parentheses refinement also passed the nine targeted overhaul tests. Python compilation and Git whitespace checks passed. Browser MCP checks confirmed an AAPL FY2025 annual view, synchronized explanation, reconciliation messages and retained five-page navigation.

## Limits and operation

Some custom definitions lack enough evidence for automatic mapping. Complex untagged headers, prose-only untagged amounts, unusual transition-quarter calendars, split-adjusted standalone EPS, and multi-unknown equations may remain unresolved. Full-year net intangible assets are not replaced by a finite-lived subset unless an exact supported reconciliation is available; Microsoft’s separately reported finite-lived amount is retained in its own row. All possible company-specific accounting presentations are not covered by this release.

Taxonomy inspection fetches at most six same-filing documents per targeted report and four already-inspected reports per lookup. Inline parsing has a 40 MB input limit and a cooperative 30-second budget; untagged parsing has a cooperative 10-second budget. DOM construction is bounded by input size, not preempted mid-call. SEC requests have 30-second timeouts, four-per-second rate control, retry/backoff, disk caching and a 403 cooldown. Authentic checksum-verified bundled responses are clearly identified as cached rather than live. No paid service or hosting dependency was introduced.

Run `python -m pip install -r requirements.txt`, set a legitimate `SEC_USER_AGENT` through environment/Streamlit secrets, then run `python -m pytest -q` and `python -m streamlit run app.py`. Do not commit the operator contact configuration. See [deployment instructions](../DEPLOYMENT.md) for the existing Community Cloud app and its tracked branch.
