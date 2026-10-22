# Free deployment

1. Install Python 3.12+, create a virtual environment, and run `pip install -r requirements.txt`.
2. Set `SEC_USER_AGENT` to `QuarterFill Your Name your-real-email` in your environment.
3. Run `python -m pytest -q`, then `python -m streamlit run app.py`.
4. Publish this repository on GitHub. In https://share.streamlit.io choose Create app,
   select `Manek-Shah25/QuarterFill`, the reviewed branch and `app.py`, Python 3.12.
5. In Streamlit Advanced settings → Secrets, set `SEC_USER_AGENT` using TOML syntax.
   Do not commit your contact configuration. Request `quarterfill.streamlit.app` if available.
6. Test a real lookup, inspect both filing sources of a calculated cell, and download Excel.
   Only then record the actual deployment URL.

Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Cloud SEC access fallback

Run `python scripts/refresh_snapshots.py --tickers AAPL MSFT --years 2024 2025`
on a machine/network permitted to access SEC. The script writes authentic cached SEC
envelopes into `data/snapshots/`, including inspected filing HTML, plus a manifest.
Publish those public SEC records on a dedicated `sec-data` branch or repository.
Set `QUARTERFILL_SNAPSHOT_URL` to its raw GitHub directory URL. Add the same
tickers/years needed by visitors; missing snapshots result in explicit access failures.
Do not promise full-universe coverage. Refresh manually or configure the included
workflow with a genuine SEC_USER_AGENT repository secret. GitHub-hosted runners may
also be blocked by SEC; failed refreshes must not overwrite good records.

Local caches are performance aids only. The application does not depend on durable
Streamlit disk. Never host a paid database or require visitor API keys.

## Publication status

Live URL verified October 22, 2026: https://quarterfill.streamlit.app
An AAPL FY2025 stock-based compensation lookup returned all four quarters and a
document-matched source audit. Deployment tracks `codex/quarterfill-implementation`.
Repository is public; the implementation remains in pull request #15 while advanced
acceptance gaps are tracked explicitly. The app uses Python 3.12 and encrypted SEC
operator configuration. No paid infrastructure was enabled.

See docs/implementation_checklist.md and docs/validation.md for measured completion.
Project board and deployment require an authenticated browser/account if connector APIs
do not provide those operations. Public visibility must be checked separately from push.
