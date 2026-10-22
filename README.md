# QuarterFill

**SEC quarterly reconstruction with cell-level evidence.** A Python/Streamlit financial
research utility that prefers reported quarters, differences compatible cumulative flows,
and preserves original filing inputs and calculation trails.

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SEC_USER_AGENT = 'QuarterFill Your Name your-real-contact-email'
python -m streamlit run app.py
```

Six pages cover quarterly lookup, supported three-statement reconstruction, missing-data
investigation, filing exploration, audited exports and methodology/data health.
Visitors need no account or paid API. Operators must configure SEC identification.

## Evidence-first engine

`quarterfill/models.py` defines immutable facts and auditable cells; `engine.py` performs
deterministic accounting; `sec.py` retrieves and parses official evidence; `research.py`
orchestrates investigation; `export.py` creates independently reviewable workbooks.
The Streamlit layer never invents a financial result or treats a blank as zero.

```sh
python -m pytest -q
```

See [accounting methodology](docs/accounting_methodology.md), [audit trail](docs/audit_trail_methodology.md),
[source coverage](docs/sec_data_sources.md), [deployment](DEPLOYMENT.md),
[validation status](docs/validation.md), and the [implementation checklist](docs/implementation_checklist.md).

## Status and limitations

This implementation is under validation. No public deployment or 15-company manual audit
is claimed. Document matching proves that a fact was located, not that cross-period
accounting bases are economically comparable. Unsupported cases remain unavailable or
require analyst review. The advanced gaps are listed explicitly in the checklist.

Financial research only; not investment, tax or accounting advice. Review original SEC
filings and use professional judgment. No warranty of completeness or suitability.

MIT License. Independent project; not affiliated with or endorsed by the SEC.
