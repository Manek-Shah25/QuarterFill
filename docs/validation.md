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
inline filing contexts** in the final run after conflict detection. Source matching coverage was 170/240 (70.83%).
The other 70 cells remained unresolved; no values were fabricated. This is coverage,
not an extraction-accuracy or reconstruction-accuracy claim. Independent manual
ground truth and complete financial review are still required.

Companies: AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA, JPM, BAC, WMT, COST, XOM,
JNJ, PG and KO. Reports in `data/validation/` preserve individual results, formulas,
contexts, source excerpts, retrieval timestamps and investigation logs. Bank revenue
definitions, CapEx concepts, legacy issuer history and unreported standalone Q4 EPS
are material unresolved cases. The original XOM history was not recovered by this
scan and is not silently substituted with another issuer.

Automated tests: 35 passed including direct-versus-YTD conflicts, segment scope, qualitative evidence and graceful historical-index failure;
see CI for the latest count. The real-data UI test exercises an AAPL FY2025 lookup
using bundled authentic SEC snapshots without a visitor key.
