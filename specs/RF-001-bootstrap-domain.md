# RF-001 — Bootstrap canonical domain

## Goal

Create the first canonical transaction and reconciliation result types without introducing framework/infrastructure dependencies into the domain.

## Acceptance criteria

- [ ] Canonical money values use `Decimal`.
- [ ] Result status is explicit.
- [ ] A `MATCHED` result cannot exist without rule ID/version/evidence.
- [ ] Domain imports no forbidden framework/infrastructure package.
- [ ] Unit tests cover valid and invalid result construction.
- [ ] `make verify` passes.

## Domain invariants touched

- Money
- Explainability
- Determinism foundations

## Architecture constraints

- implementation belongs under `reconcileflow/domain`;
- no FastAPI, SQLAlchemy, pandas, polars, Celery, Redis.

## Non-goals

- persistence;
- HTTP endpoints;
- CSV/XLSX parsing;
- tolerance matching.

## Verification

```bash
make verify
```

## Evidence required

- unit tests;
- architecture check result.
