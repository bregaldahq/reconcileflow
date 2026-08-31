# Quality strategy

`make verify` is the authoritative gate. It performs:

1. repository/document/fixture consistency checks;
2. architecture-boundary checks;
3. Ruff formatting and linting;
4. mypy strict typing for the backend;
5. unit, property, golden, contract, integration, and deterministic tests with coverage;
6. Alembic migration validation;
7. frontend formatting/type/lint/unit checks and production build;
8. Python and Node dependency audits, Bandit, and committed credential-pattern scanning.

Tests are labeled but run together by default. Golden scenarios assert full stable decisions and explanations. Determinism tests permute input order. Property tests cover money rejection, normalization idempotence, one-participant ownership, and split amount conservation.

Performance checks use generous deterministic budgets and explicit worst-case fixture sizes; they are regression alarms, not microbenchmarks.
