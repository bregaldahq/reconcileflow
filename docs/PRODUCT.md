# Product

ReconcileFlow helps finance operations teams compare two transaction datasets without hiding judgment inside a spreadsheet. A user uploads CSV/XLSX files, maps columns, selects a rule profile, runs reconciliation, reviews explainable outcomes, records manual decisions, and exports a workbook.

## Primary journey

1. Upload and validate datasets A and B.
2. Inspect deterministic fingerprints and map fields to the canonical schema.
3. Normalize using an explicit normalization version.
4. Start a run using a versioned rule-set snapshot.
5. Observe queued/running/completed progress.
6. Inspect `MATCHED`, `SPLIT_MATCHED`, `UNMATCHED`, `AMBIGUOUS`, `DUPLICATE`, and `MANUAL_REVIEW` outcomes.
7. Review evidence and append an approve/reject audit event.
8. Export an XLSX report and reproduce prior runs from immutable inputs and configuration.

## Users and success

The primary user is a reconciliation analyst. Success means they can explain each automatic result, see unresolved risk immediately, and reproduce a completed run. The demo uses synthetic Brazilian-style identifiers and currency formats; no real personal or financial data belongs in the repository.
