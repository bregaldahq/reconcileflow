# Prompt — Bootstrap the ReconcileFlow harness

You are bootstrapping an agent-native software engineering repository.

Read first:

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/DOMAIN.md`
- `docs/QUALITY.md`
- `specs/RF-001-bootstrap-domain.md`

Your goal is NOT to build the whole product.

Your goal is to make the repository ready for safe incremental implementation.

## Tasks

1. Implement RF-001.
2. Add the initial domain package and tests.
3. Make the architecture checker enforce the documented boundaries.
4. Ensure `make verify` runs the appropriate checks for the current stage.
5. Configure Ruff, mypy and pytest.
6. Keep external/runtime dependencies minimal.
7. Do not add FastAPI/database/dataframe libraries until a task actually requires them.
8. Once the implementation quality gate is real and green, change `.harness-stage` from `bootstrap` to `implementation`.

## Constraints

- Do not invent additional product features.
- Do not weaken checks.
- Do not move business logic into scripts just to satisfy tests.
- Keep the domain independent of frameworks.

## Completion

Do not claim completion until:

```bash
make verify
```

passes.

Then summarize:

- files changed;
- architectural decisions;
- tests/checks executed;
- evidence of the passing quality gate;
- next recommended task.
