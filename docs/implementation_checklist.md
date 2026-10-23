# Implementation checklist

The October 23 overhaul supersedes the export-control wording below: it restores a
small per-statement Excel download, while retaining the five pages and no Export
Center. It adds broader mappings, guarded recovery, report-version views and statement
checks. [Current extraction scope and evidence](extraction-overhaul.md) records the
seven-company benchmark and the remaining semantic and transition-period limits.

## Current website scope

The user requested a simpler website on October 22, 2026. The frontend now focuses on
financial statements and clear explanations of missing-number calculations. It keeps
five pages, removes Excel Export Center and other export/import controls, and hides
internal accounting tags, record IDs and request logs. The export engine remains in
the source for compatibility; it is not part of the website. Earlier advanced goals
below are historical requirements, not claims about the simplified interface.

- [x] Company and year lookup with five retained pages
- [x] Plain-language, numbered calculation explanations with exact amounts and report links
- [x] Simplified Methodology and Data Health page
- [x] No developer tags, internal IDs, archive tools or export center in the frontend
- [x] README begins with the user problem and explains the pages in everyday language

- [x] Modular Python engine and six Streamlit page routes
- [x] Supported metric dictionary, definition choices and alias search
- [x] CompanyFacts/submissions ingestion, primary inline investigation and request cache
- [x] Actual fiscal boundary selection, additive Q1–Q4 and instant selection
- [x] Conservative EPS/nonadditive handling and retained filing conflicts
- [x] Stable fact/cell IDs, audit JSON, source excerpts and source-match criteria
- [x] Basic three-statement builder and explicitly defined derived metrics
- [x] Four-sheet Excel export and explicit empty-cell-only model mapping
- [x] Deterministic financial regression tests and CI configuration
- [ ] Full advanced SEC investigation coverage (see sec_data_sources.md)
- [ ] Automated positive evidence for not-applicable/not-separately-disclosed
- [x] Explicitly selected custom/segment concept and dimensional-scope reconstruction UI
- [x] Literal-source-backed qualitative analyst classification with downloadable evidence
- [ ] Automated semantic verification of custom accounting definitions
- [ ] Split/dilution-aware EPS derivation
- [ ] Complete manual review of at least 15 companies and measured accuracy
- [x] Confirmed public repository and five-status project board with 14 workstream issues
- [x] Hosted CI passed on published engine/UI commits; final documentation checks tracked in Actions
- [x] Live Streamlit deployment and authentic AAPL FY2025 lookup/audit verified

This checklist distinguishes implemented code from the full acceptance requirements.
