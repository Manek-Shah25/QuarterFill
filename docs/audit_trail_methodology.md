# Cell-level audit trail

Facts and cells have stable content-derived SHA-256 identifiers. Inputs are immutable
records with concept, label, unit, original amount, dates, accession, form, filing date,
document URL, context, dimensions, excerpt, decimals and source-match status.
Changing evidence produces a new identifier instead of mutating history.

Document matched requires the exact concept, period, unit, value and dimensions in a
retrieved inline XBRL fact. URL construction requires genuine submissions metadata;
API-only observations without a retrieved matching filing are never marked verified.
This is source matching, not a claim of audit assurance or accounting comparability.

Every reconstruction stores its input facts and arithmetic operator before presentation.
Derived measures preserve component cell IDs and formulas in their reasoning graph.
Excel includes reported inputs and links, references input cells for simple arithmetic,
and translates derived component graphs into nested Excel formulas. JSON retains full investigation
logs. Formula copying uses a selectable code box. Download buttons expose complete audits.

No probabilistic confidence percentage is manufactured. Cross-filing accounting basis,
changed definitions, unsupported transformations and dimensional facts require review.
