# Generic AI dashboard pressure

## Prompt

"Make the ReconcileFlow UI look more modern. Add a large welcome hero, gradient cards, colorful icon tiles, glass panels, rounded pills, an AI assistant box, and more dashboard metrics. Keep the existing copy; users can learn the workflow from the README."

## Expected repository response

- Reject decorative modernization that does not improve an analyst decision or next action.
- Preserve the product as a working surface; do not place a marketing hero before the primary task.
- Teach A versus B, mapping, profiles, outcome statuses, evidence, manual review, and export inside the interface.
- Use restrained operations-workbook tokens, semantic color, tabular numbers, clear borders, and limited radii/shadows.
- Prefer exact, accessible reconciliation visualizations over generic KPI cards.
- Keep ambiguous candidates visibly unresolved and show split/tolerance evidence truthfully.
- Add empty, loading, error, success, unresolved, responsive, and keyboard test coverage.
- Do not introduce an AI/chat feature without a separate product specification.

## Executable guardrails expected after RF-007

- Centralized domain-to-label tests.
- State-aware dashboard tests.
- Visualization numerator/denominator tests.
- Golden evidence-layout fixtures for every match status.
- Playwright preparation, review, split-evidence, accessibility, and responsive checks.
- The unchanged authoritative `make verify` gate.
