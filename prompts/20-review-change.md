# Prompt — Independent review

Act as an independent reviewer.

Do not assume the implementation agent made good decisions.

Read:

- `AGENTS.md`
- `ARCHITECTURE.md`
- `docs/DOMAIN.md`
- the task spec
- the diff

Review specifically for:

1. violated domain invariants;
2. hidden nondeterminism;
3. silent ambiguity;
4. money represented as float;
5. business logic leaking into transport/infrastructure;
6. tests that merely mirror implementation;
7. missing failure cases;
8. missing rule/version/explanation metadata;
9. weakened checks;
10. docs/contracts out of sync.

Run `make verify`.

If you find a defect, propose or implement the smallest correction and rerun verification.

Return a concise review with evidence, not a generic approval.
