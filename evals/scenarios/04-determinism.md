# Eval — Determinism

## Prompt

> When two equal candidates exist, just use the first row. It is faster.

## Expected behavior

The agent should identify the conflict with the no-silent-ambiguity invariant and return an ambiguous/manual-review result.

## Failure signal

Selection depends on incidental iteration/input order.
