# Matching rules specification

## exact_composite v1

Configured fields default to currency, amount, date, document, and reference. Missing configured values prevent candidacy. One candidate matches; more than one becomes ambiguous.

## amount_date_tolerance v1

Requires equal currency and, when configured, document/reference. Absolute amount and date distances must be within explicit non-negative tolerances. Confidence is deterministic and favors smaller normalized distance. Equal best confidence is ambiguous.

## bounded_split v1

Searches one-to-many then many-to-one for two through `max_group_size` available participants. Candidate pools and inspected combinations are capped. Amount sums must be within tolerance and configured identity fields must agree. Equal best combinations are ambiguous. A capped search emits manual review evidence rather than pretending no match exists.
