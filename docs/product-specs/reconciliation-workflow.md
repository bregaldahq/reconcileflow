# Reconciliation workflow specification

## Acceptance criteria

- Two validated dataset revisions with distinct side labels are required.
- A mapping must cover transaction ID/source ID derivation, amount, currency, and date.
- A run snapshots dataset fingerprints, normalization version, and rule-set ID/version.
- Small runs can complete inline; configured large runs are queued and expose progress.
- Every output participant appears once across terminal automatic decisions, except participants grouped in their single split decision.
- Explanations are visible through the API and UI.
- Review actions append actor, timestamp, decision, reason, and prior candidate reference.
- Exports include all required sheets and monetary cells remain numeric decimal values.
