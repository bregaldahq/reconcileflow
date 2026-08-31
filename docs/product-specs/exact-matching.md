# Exact Matching

## Rule ID

`exact_composite`

## Intent

Automatically match records when a configured canonical composite key is equal.

Example key:

- amount;
- normalized document;
- transaction date.

## Required behavior

- exact equality after canonical normalization;
- one unique candidate => `MATCHED`;
- zero candidates => continue/unmatched;
- multiple equally valid candidates => `AMBIGUOUS`;
- result contains rule/version/evidence.

## Non-goal

This rule does not perform fuzzy/tolerance matching.
