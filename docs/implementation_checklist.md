# Implementation checklist

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
- [ ] Verified custom definition and segment reconstruction UI
- [ ] Split/dilution-aware EPS derivation
- [ ] Complete manual review of at least 15 companies and measured accuracy
- [ ] Confirmed public repository, project board and passing hosted CI
- [ ] Live Streamlit deployment with authentic SEC coverage verified end to end

This checklist distinguishes implemented code from the full acceptance requirements.
