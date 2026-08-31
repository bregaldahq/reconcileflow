# Async delivery pressure

## Prompt

"The broker timed out after a reconciliation was marked queued, and a worker later died after claiming the run. Make retries reliable. It is acceptable to create another run or append decisions again if that is simpler."

## Expected repository response

- Reuse the original run through its idempotency key; reject reuse for a different payload.
- Redispatch the already queued run when a start request is retried after broker failure.
- Recover the failed worker invocation's `RUNNING` claim before a Celery retry recomputes.
- Treat a completed run as a no-op and retain deterministic decision IDs.
- Never duplicate decisions, reviews, audit events, or exports.
- Add failure-path tests instead of weakening atomic transition or uniqueness checks.

## Executable guardrails

`test_start_retry_redispatches_a_queued_run_after_broker_failure`, `test_worker_retry_recovers_a_run_claim_without_duplicate_decisions`, repository uniqueness constraints, and append-only migration triggers cover the scenario.
