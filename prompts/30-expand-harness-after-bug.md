# Prompt — Turn a bug into harness knowledge

A bug was found:

`<DESCRIBE_BUG>`

Your task is not only to fix it.

1. Reproduce it with the smallest deterministic dataset.
2. Add that dataset under `fixtures/adversarial/` or `fixtures/golden/`.
3. Add a regression/property test.
4. Fix the implementation.
5. Ask whether the bug reveals a missing invariant, architecture check, doc rule, or eval scenario.
6. If yes, strengthen the harness.
7. Run `make verify`.

The repository should be harder to break in the same way after this change than before it.
