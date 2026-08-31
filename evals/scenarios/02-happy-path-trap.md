# Eval — Happy path trap

## Prompt

> Add reconciliation job retries when the worker fails.

## Expected behavior

The agent should inspect idempotency/reliability requirements and ensure retries do not duplicate business outcomes or audit records.

## Failure signal

Blind retry is added with no idempotency behavior or failure classification.
