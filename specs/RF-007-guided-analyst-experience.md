# RF-007 — Guided analyst experience

Status: Proposed implementation plan

## Goal

Replace the generic dashboard presentation with a task-oriented finance operations interface that teaches a first-time analyst how to prepare, run, understand, review, and export a reconciliation.

## Context

The product journey is implemented, but the current visual hierarchy leads with dashboard conventions rather than the analyst's next task. Guidance is mostly promotional copy, while result explanations are prose-heavy and important distinctions are spread across cards, tables, and a drawer.

The governing UX behavior is defined in `docs/product-specs/analyst-guidance-and-visualizations.md`.

## Delivery slices

### RF-007A — Language and visual foundation

- [ ] Introduce centralized pt-BR labels for navigation, actions, statuses, and errors without changing API enums.
- [ ] Replace broad theme styles with operations-workbook tokens for color, type, spacing, borders, radii, focus, and semantic states.
- [ ] Simplify `AppShell`: task-based navigation, visible `Como funciona` entry, no decorative environment/avatar chrome.
- [ ] Create reusable `ContextGuide`, `OutcomeLegend`, `SourceSummary`, and `EvidenceFlow` primitives using existing React/CSS architecture.
- [ ] Remove generic greetings, promotional slogans, decorative icon containers, serif KPI figures, gradients, and excessive pills.

Focused verification:

```bash
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run build
```

### RF-007B — First-use home and contextual guide

- [ ] Make the empty home state explain the business problem, A versus B, the four workflow steps, accepted files, and the first action in the initial viewport.
- [ ] Make populated home states prioritize exactly one next action: continue processing, resolve exceptions, inspect completion, or start a new run.
- [ ] Keep history and aggregate counts secondary.
- [ ] Provide a concise `Como funciona` guide with concrete exact, tolerance, split, ambiguous, duplicate, and unmatched examples.
- [ ] Test empty, active, unresolved, and completed home states.

Focused verification:

```bash
npm --prefix frontend run test -- DashboardPage Guide
```

### RF-007C — Explainable preparation workflow

- [ ] Rework the flow into `Escolher fontes`, `Conferir colunas`, `Definir comparação`, and `Revisar e iniciar`.
- [ ] Explain Dataset A/B with concrete source examples adjacent to upload controls.
- [ ] Visualize source comparison and mapping completeness using only data already returned by the API.
- [ ] Explain required canonical fields, guessed mappings, tolerances, split bounds, and expected result categories.
- [ ] Prevent forward navigation when requirements are incomplete and state exactly how to recover.
- [ ] Add a preflight summary with both fingerprints, row counts, mappings, profile version, and limits.
- [ ] Test happy path, invalid mapping, existing datasets, small viewport, and keyboard navigation.

Focused verification:

```bash
npm --prefix frontend run test -- WorkflowPage
npm --prefix frontend run test:e2e
```

### RF-007D — Truthful result visualizations

- [ ] Lead with completion and unresolved work rather than four equal metric cards.
- [ ] Add a segmented outcome bar with exact counts and an accessible table alternative.
- [ ] Label the denominator explicitly; do not mix participant counts and decision counts.
- [ ] Reorder tabs and table columns around analyst actions and recognizable source data.
- [ ] Replace the generic evidence drawer with exact, tolerance, split, ambiguous, and duplicate evidence layouts.
- [ ] Show split conservation equations and tolerance deltas using decimal-safe display logic.
- [ ] Keep rule IDs, versions, fingerprints, and run IDs in a secondary reproducibility section.
- [ ] Test every match category with golden UI fixtures.

Focused verification:

```bash
npm --prefix frontend run test -- RunDetailPage Evidence
```

### RF-007E — Review, audit, accessibility, and responsive QA

- [ ] Group review work by reason and explain why automation stopped.
- [ ] Confirm that reviewed decisions leave the unresolved queue while append-only history remains visible.
- [ ] Make approve/reject copy describe the effect and preserve the required reason.
- [ ] Verify semantic headings, labels, focus order, keyboard operation, reduced motion, and color-independent states.
- [ ] Add Playwright assertions at 360 px, 768 px, and desktop widths for first action visibility, no unexpected page overflow, evidence readability, and review completion.
- [ ] Capture deterministic before/after evidence for the portfolio documentation after the implementation is complete.

Focused verification:

```bash
npm --prefix frontend run verify
```

## Acceptance criteria

- [ ] Given a repository with no datasets or runs, when a first-time analyst opens the home screen, then the initial viewport explains A versus B, shows the four-step workflow, and exposes one primary action.
- [ ] Given uploaded datasets, when the analyst maps columns, then every required field explains its purpose and incomplete requirements identify the exact recovery action.
- [ ] Given a selected profile, when the analyst reaches preflight, then exact, tolerance, split behavior, versions, limits, and source fingerprints are visible before execution.
- [ ] Given a completed run, when results load, then the dominant visualization identifies reconciled versus unresolved work with exact labeled counts and a stated denominator.
- [ ] Given an automatic decision, when its evidence opens, then source records, applied rule, target records, configured limits, and conclusion are understandable without API terminology.
- [ ] Given equal candidates, when the analyst reviews the decision, then all candidates remain visibly equal and the UI never implies an automatic winner.
- [ ] Given a split match, when its evidence opens, then the displayed equation conserves the source and target amounts using decimal-safe values.
- [ ] Given a keyboard-only or narrow-viewport user, when they complete the primary journey, then all actions and explanations remain accessible and usable.
- [ ] Empty, loading, error, processing, success, unresolved, and reviewed states have focused automated coverage.
- [ ] `make verify` remains green; coverage thresholds and architecture checks are not weakened.

## Domain invariants touched

- UI amount calculations must preserve Decimal/string representations.
- Ambiguous candidates remain unresolved until an append-only review event exists.
- Completed runs and automatic decisions remain immutable.
- Rule and normalization versions remain visible in reproducibility evidence.
- Participant ownership and split conservation must not be misrepresented visually.

## Architecture constraints

- Keep the redesign in the existing React, TypeScript, TanStack Query, and CSS structure unless a concrete requirement proves a missing primitive.
- Presentation components consume API contracts; business matching logic does not move into React.
- Any derived visualization metric has a pure, tested formatter/select function and an explicit denominator.
- Routes orchestrate queries and states; reusable evidence and visualization components remain presentational.
- No new backend endpoint is part of the initial redesign. A masked preview contract requires a separate spec and security review if later justified.

## Harness changes required during implementation

- Add UI fixtures for all six match statuses plus async and error states.
- Add component tests for instruction hierarchy, state-aware next actions, visualization totals, and evidence layouts.
- Extend Playwright from one happy path to preparation, ambiguity review, split evidence, and responsive overflow checks.
- Add accessibility assertions for names, roles, focus, and text alternatives. Adopt an automated accessibility library only if native assertions cannot cover the acceptance criteria.
- Update portfolio screenshots only after `make verify` passes.
- Keep `evals/generic-ai-dashboard-pressure.md` as a standing agent-pressure scenario.

## Non-goals

- Matching-engine, confidence, persistence, or worker changes.
- Raw transaction preview API.
- AI chat, recommendations, predictions, or decorative analytics.
- Replacement of the frontend stack or a broad component-library migration.
- External hosting.

## Risks and mitigations

- **Instruction overload:** progressive disclosure; keep one sentence of context and one next action visible, with detail in contextual help.
- **Misleading metrics:** use participant totals or explicitly label decision counts; test numerator and denominator.
- **Color-heavy status design:** require text and structural labels in every state.
- **Responsive loss of evidence:** preserve evidence order and allow only the detailed table to scroll horizontally.
- **Translation drift:** centralize visible labels and test stable domain-to-label mappings.
- **Visual regression fragility:** begin with semantic and viewport assertions; add pixel baselines only after fonts and CI rendering are deterministic.

## Verification

```bash
make verify
```

## Evidence required

- before/after captures for empty home, preparation preflight, completed result, split evidence, and ambiguous review;
- automated coverage for each documented state and status;
- Playwright evidence at mobile and desktop widths;
- final `make verify` output;
- short usability walkthrough showing that a new user can explain the workflow without external documentation.
