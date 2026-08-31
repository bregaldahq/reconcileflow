# Tolerance Matching

## Rule ID

`amount_date_tolerance`

## Intent

Match records that agree on required identifiers but differ within explicitly configured amount/date tolerances.

## Required behavior

- tolerances are configuration, not hidden constants;
- confidence/explanation reflects the differences;
- equally valid candidates remain ambiguous;
- rule execution is deterministic.

## Example

```text
ERP:  1250.00 on 2026-08-25
Bank: 1250.00 on 2026-08-26
Configured date tolerance: 2 days
```

Expected: candidate can be accepted with `date_difference_days = 1`.
