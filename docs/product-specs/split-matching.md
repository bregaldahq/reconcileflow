# Split Matching

## Rule ID

`bounded_split`

## Intent

Model one-to-many or many-to-one reconciliation when amounts are split/aggregated between systems.

## Required behavior

- bounded candidate search;
- exact or configured decimal tolerance;
- no source/target is consumed inconsistently;
- explanation lists every participating record;
- performance limits are explicit;
- ambiguous combinations are not silently chosen.

## Example

```text
Source: 500 + 300 + 200
Target: 1000
```

Expected: one explainable `SPLIT_MATCHED` decision if the candidate set is unique.
