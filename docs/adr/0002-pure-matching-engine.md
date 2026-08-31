# ADR-0002 — Pure matching engine

## Status
Accepted

## Decision

The core matching engine must not perform I/O or depend on web frameworks, persistence libraries or dataframe libraries.

## Reason

The matching engine needs:

- deterministic behavior;
- fast unit/property testing;
- reproducibility;
- portability;
- simple agent feedback loops.

## Consequence

Parsing, persistence and orchestration live outside the domain.
