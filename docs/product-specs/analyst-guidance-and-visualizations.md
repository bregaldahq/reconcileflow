# Analyst guidance and visualizations

Status: Proposed

## Problem

The current interface communicates implementation maturity more strongly than it teaches reconciliation. It relies on a familiar AI-generated dashboard vocabulary: a greeting, repeated cards, decorative icon containers, many eyebrow labels, soft shadows, rounded pills, and abstract trust copy. A first-time analyst still has to infer what Dataset A and Dataset B mean, why column mapping exists, what each rule does, and which result requires action.

The redesign must feel like a finance operations workspace: calm, explicit, information-dense when needed, and instructional without becoming a marketing page.

## User and job

The primary user is a finance operations analyst who may understand spreadsheets but not matching-engine terminology. Their job is to:

1. understand which two sources should be compared;
2. prepare both sources correctly;
3. understand the selected matching behavior before running it;
4. identify what reconciled and what needs attention;
5. understand and record a defensible manual decision;
6. export evidence.

The interface must answer three questions on every primary screen:

- What am I doing here?
- What did ReconcileFlow find?
- What should I do next?

## Target mental model

Use one stable product sequence everywhere:

`Prepare sources -> Compare -> Resolve exceptions -> Export evidence`

Dataset A is described as the internal/source-of-truth ledger. Dataset B is described as the external/settlement source. These descriptions are examples, not new domain invariants; the underlying sides remain `A` and `B`.

## Language and terminology

The demo interface defaults to plain Brazilian Portuguese. Domain values and API enums remain unchanged, but visible labels use:

| Domain value | Visible label | Explanation |
| --- | --- | --- |
| `MATCHED` | Conciliado | One record or pair satisfied a configured automatic rule. |
| `SPLIT_MATCHED` | Conciliado em grupo | One side corresponds to the sum of multiple records on the other side. |
| `UNMATCHED` | Sem correspondência | No configured rule produced a candidate. |
| `AMBIGUOUS` | Mais de uma possibilidade | Two or more candidates were equally valid; no winner was chosen. |
| `DUPLICATE` | Possível duplicidade | Canonically equal records exist on the same side. |
| `MANUAL_REVIEW` | Revisão necessária | Automatic search stopped at a safety boundary or requires judgment. |

Internal run IDs, fingerprints, rule IDs, and versions remain available as secondary audit metadata. Primary labels use file names, dates, amounts, and actions the analyst recognizes.

Avoid greetings, marketing slogans, vague confidence language, and internal jargon without an adjacent explanation. Buttons use explicit verbs such as `Selecionar arquivo`, `Validar colunas`, `Iniciar conciliação`, `Revisar possibilidades`, and `Exportar relatório`.

## Information architecture

### Home

The first viewport is state-aware rather than a generic KPI dashboard.

- With no data, show `Comece sua primeira conciliação`, a four-step checklist, the difference between sources A and B, accepted file formats, and one primary action.
- With work in progress, lead with the active run and its next meaningful state.
- With unresolved exceptions, lead with the review workload and a direct action.
- With completed work and no exceptions, lead with the latest completed reconciliation and export/review links.

Historical counts remain secondary. Remove decorative metrics that do not change a decision.

### New reconciliation

Use four explicit steps:

1. `Escolher fontes`: explain A versus B and upload/choose each file.
2. `Conferir colunas`: show source column -> canonical field mappings, required fields, guessed mappings, and a plain-language example for each canonical field.
3. `Definir comparação`: explain exact, tolerance, and grouped matching using the current profile values.
4. `Revisar e iniciar`: summarize both fingerprints, row counts, mapping completeness, tolerance values, split-search bounds, and the expected outputs before the run starts.

A persistent contextual guide occupies a narrow secondary rail on desktop and a collapsible `Ajuda desta etapa` region on small screens. It never blocks the primary action.

### Run result

Order the screen by analyst decision priority:

1. completion status and the next recommended action;
2. outcome distribution and reconciliation coverage;
3. unresolved exceptions;
4. filterable detailed records;
5. reproducibility metadata and export.

The table remains the authoritative detailed representation. Visualizations summarize; they never replace exact values or evidence.

### Decision explanation

Replace a prose-heavy drawer with an evidence flow:

`Source record(s) -> Applied rule -> Target record(s)`

Show amounts, dates, normalized identifiers, differences, configured limits, and a concise conclusion. For ambiguous decisions, compare each candidate in aligned rows. For split decisions, show the amount equation and conservation result. Manual approve/reject controls appear after the evidence, not before it.

### Review queue and audit

The review queue groups work by reason (`multiple possibilities`, `search limit`, `possible duplicate`) and states why automatic resolution was unsafe. Reviewed decisions leave the unresolved queue but remain visible in the append-only audit history.

## Visualization requirements

### Outcome distribution

Use a horizontal segmented bar plus a numeric legend. Segments represent participant records, not decision objects. If the required participant totals are unavailable, the UI must label the visualization as decision counts rather than presenting a misleading match rate.

Required accessible alternative: a text/table summary containing every category, exact count, and denominator.

### Source comparison

Before a run, show a two-column comparison:

- source name and side;
- row and column counts;
- mapping completeness;
- fingerprint abbreviation;
- validation result.

The visualization emphasizes differences that block progress. It must not expose more raw financial data than the existing API already returns.

### Match evidence

- Exact: aligned field comparison with equal values marked textually.
- Tolerance: amount delta and date delta shown against the configured limits.
- Split: equation such as `R$ 500 + R$ 300 + R$ 200 = R$ 1.000`, including a conservation check.
- Ambiguous: candidate comparison matrix with the tied score and differing fields.
- Duplicate: grouped records with the canonical fields that caused duplication.

Color is supplementary. Every meaning is also communicated through text, shape, label, or icon.

## Visual direction

The design language is an operations workbook, not a promotional dashboard.

- Use a neutral warm-gray canvas, white working surfaces, dark ink, and one restrained blue-teal interaction color.
- Reserve green, amber, and red for semantic states only.
- Use a system sans-serif stack with tabular numerals. Monospace is limited to fingerprints and technical IDs.
- Use a 4/8/12/16/24/32 spacing scale.
- Use 4-8 px corner radii. Pills are reserved for compact statuses and filters.
- Use borders and spacing for hierarchy; shadows are rare and shallow.
- Remove gradients, glass effects, decorative icon tiles, oversized greetings, serif KPI numerals, repeated eyebrow labels, and marketing-style trust panels.
- Icons accompany labels only when they improve recognition. They are not decoration.
- Motion is limited to progress, disclosure, and state transition, with reduced-motion support.

## Required states

Every primary screen defines and tests:

- first-use/empty;
- loading or asynchronous processing;
- validation error with a recovery action;
- partial completion;
- successful completion;
- unresolved review work;
- no review work;
- narrow viewport and keyboard-only use.

## Accessibility and responsive behavior

- Meet WCAG AA contrast for text and controls.
- Do not rely on color alone.
- Preserve a logical heading hierarchy and visible focus.
- Charts expose a table or equivalent accessible description.
- Core tasks are keyboard operable.
- At 360 px, instructions precede controls, primary actions remain visible, and only data tables may scroll horizontally.
- At desktop widths, instructional rails must not reduce the main working surface below a useful table width.

## Data truth constraints

- Monetary values remain strings/`Decimal` across contracts; visualization code must not introduce binary-float calculations.
- UI translations do not change persisted enum values.
- Match rate, coverage, and totals must state their denominator.
- Automatic decisions remain immutable; a manual review is displayed as a separate event.
- No visualization may hide ambiguity, collapse equal candidates into a winner, or imply certainty not present in evidence.

## Non-goals

- New matching rules or changes to matching confidence.
- A conversational assistant or chat interface.
- Decorative analytics, forecasts, trends, or benchmarking without a product decision they support.
- A new component framework solely to restyle existing controls.
- Production identity, tenant management, or external deployment.

## Success criteria

- A first-time user can describe A versus B and the four-step workflow from the first viewport.
- Each step explains why the requested information matters and exposes one clear next action.
- The result screen makes unresolved work more prominent than completed history.
- Every visualization has exact numeric and accessible evidence.
- A reviewer can explain exact, tolerance, split, ambiguous, and duplicate outcomes without reading raw API enums.
