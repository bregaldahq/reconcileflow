# ReconcileFlow engineering contract

This repository is built in small, verified vertical slices. Read this file and the documents linked from `ARCHITECTURE.md` before changing behavior.

## Non-negotiable rules

- Run `make verify` before declaring work complete. Do not weaken a check to make it pass.
- Keep `reconcileflow.domain` free of FastAPI, SQLAlchemy, Redis, Celery, Polars, pandas, HTTP, and file-format imports.
- Use `Decimal` for money. Floats are rejected at every monetary boundary.
- Matching is deterministic. Stable IDs and sorted evidence are required; incidental input order never breaks a tie.
- Automatic matches carry rule ID/version, confidence, participants, and human-readable evidence.
- Equal best candidates are `AMBIGUOUS`; never choose one by order.
- A transaction participates in at most one automatic decision, except within one explicit split decision.
- Completed runs are immutable. Manual decisions and audit events are append-only.
- Dataset fingerprints are SHA-256 hashes of deterministic bytes.
- Never log raw transaction values or source documents.

## Dependency direction

`api/adapters -> application -> domain`

The application layer defines ports. Adapters implement them. Controllers translate and orchestrate only.

## Change workflow

1. Update or add a spec for behavior changes.
2. Add a failing focused test or fixture.
3. Implement the smallest complete slice.
4. Run focused checks, then `make verify`.
5. Keep fixtures synthetic and documentation truthful.

## Repository map

- `backend/src/reconcileflow/domain`: pure domain and matching engine
- `backend/src/reconcileflow/application`: use cases and ports
- `backend/src/reconcileflow/adapters`: persistence, files, queue, reports
- `backend/src/reconcileflow/api`: FastAPI transport
- `frontend`: React client
- `specs`: executable-task acceptance criteria
- `fixtures`: synthetic golden/adversarial datasets
- `evals`: agent-pressure scenarios
- `scripts`: authoritative harness helpers
