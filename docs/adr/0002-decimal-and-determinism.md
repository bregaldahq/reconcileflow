# ADR 0002: Decimal arithmetic and canonical ordering

Status: Accepted

Money and confidence use `Decimal`. Floats are rejected instead of silently converted. Candidate keys, participant IDs, and evidence are canonically sorted. Equal best choices become ambiguity.

This makes results reproducible across input order and avoids binary rounding errors. It requires explicit parsing at transport and file boundaries.
