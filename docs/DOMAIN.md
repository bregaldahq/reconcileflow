# Domain model and invariants

## Canonical transaction

A canonical transaction has a stable `transaction_id`, dataset side, `Decimal` amount, ISO currency, date, optional normalized document/reference, and source row ID. IDs are unique within a dataset. Currency codes are uppercase ISO-like three-letter values.

## Normalization

Normalization is an explicit versioned transformation. Version `br-v1` accepts unambiguous Brazilian and invariant monetary formats, rejects floats, strips document punctuation, collapses whitespace, converts empty markers to `None`, parses approved date formats, and derives missing source IDs from dataset fingerprint plus row number.

## Matching

Rules are ordered by the rule-set profile, but all candidate sets and evidence are sorted. Rules never use iteration order to resolve equality. Confidence is a `Decimal` between zero and one.

The pipeline supports exact composite, amount/date tolerance, and bounded split matching. Exact matching uses configured canonical fields. Tolerance confidence is derived only from configured bounds and exact decimal/date distances. Split matching searches combinations up to configured participant/candidate limits and conserves amount exactly within configured tolerance.

## Statuses

- `MATCHED`: one unique automatic one-to-one candidate
- `SPLIT_MATCHED`: unique one-to-many or many-to-one group
- `UNMATCHED`: no automatic candidate after the pipeline
- `AMBIGUOUS`: two or more equally valid best candidates/combinations
- `DUPLICATE`: identical canonical records on the same dataset side
- `MANUAL_REVIEW`: unresolved item routed for analyst action

## Lifecycle

Runs move `PENDING -> QUEUED -> RUNNING -> COMPLETED|FAILED`. Completed runs and automatic decisions are immutable. Manual review decisions are new append-only events; they do not rewrite historical automatic decisions.
