# Validation status

Synthetic unit tests are explicitly fixtures, never company results. They test Q1–Q4,
annual arithmetic, exact instant selection, nonadditive exclusions, changed filings,
dimensions, incompatible units, sign preservation, custom tags, missing versus zero,
noncalendar 53-week calendars, stable audit IDs, Excel input references and model protection.

Real-company validation is separate and recorded in `data/validation/` when run.
No extraction accuracy, reconstruction accuracy or source-coverage percentage is claimed
without a recorded denominator and comparison against retrieved original documents.
Automated inline matching is not a substitute for the requested manual 15-company review.
Manual review is pending until a completed reviewer record explicitly says otherwise.

## Actual run, October 22, 2026

Fifteen companies, FY2025, four metrics (Revenue, CapEx, Cash, Diluted EPS), four
quarters each: **240 requested cells; 170 returned values; all 170 matched exact
inline filing contexts** in the recorded benchmark after conflict detection, before the later comparative-precision recovery change. Source matching coverage was 170/240 (70.83%).
The other 70 cells remained unresolved; no values were fabricated. This is coverage,
not an extraction-accuracy or reconstruction-accuracy claim. Independent manual
ground truth and complete financial review are still required.

Companies: AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA, JPM, BAC, WMT, COST, XOM,
JNJ, PG and KO. Reports in `data/validation/` preserve individual results, formulas,
contexts, source excerpts, retrieval timestamps and investigation logs. Bank revenue
definitions, CapEx concepts, legacy issuer history and unreported standalone Q4 EPS
are material unresolved cases. The original XOM history was not recovered by this
scan and is not silently substituted with another issuer.

Automated tests cover direct-versus-YTD conflicts, segment scope, qualitative evidence, historical-index failures,
rounding precision changes, universal exact-ticker resolution and real NEOG/AAPL UI lookups;
see CI for the latest count. The real-data UI test exercises an AAPL FY2025 lookup
using bundled authentic SEC snapshots without a visitor key.

## Ticker identity regression

Latest local suite: **44 tests passed**, including live-data fixture lookups for AAPL and NEOG.

All 10,428 symbols in the acquired official SEC company index were tested in original,
lowercase and whitespace-padded forms. Each exact symbol resolves uniquely to its own
CIK. Exact symbol lookup precedes punctuation aliases and all company-name searches.
NEOG and NEO therefore remain distinct; the fix is not a company-specific exception.

NEOG FY2025 stock compensation: Q1 $3,982,000; Q2 $4,819,000; Q3 $4,160,000;
Q4 $4,330,000. Later comparative disclosures use coarser rounding for some inputs.
The engine retrieves those versions, checks their original XBRL decimals and retains
the more precise compatible original. Material differences remain ambiguous.

Annual source: https://www.sec.gov/Archives/edgar/data/711377/000095017025100064/neog-20250531.htm
Nine-month source: https://www.sec.gov/Archives/edgar/data/711377/000095017025052497/neog-20250228.htm
