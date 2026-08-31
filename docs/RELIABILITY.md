# Reliability

- Start-run idempotency keys uniquely identify the requested dataset/profile combination.
- Worker tasks may be delivered more than once. The run repository acquires a run transition atomically and treats completed work as a no-op. A Celery retry explicitly recovers the prior invocation's `RUNNING` claim through `QUEUED` before recomputing the deterministic result.
- Audit events and exports use stable idempotency keys with database uniqueness constraints.
- Retryable failures are transient database, queue, and storage failures. Validation, unsupported formats, and invariant violations are permanent.
- Parsing limits file size, row count, sheet count, cell text length, and accepted types.
- Split matching is bounded by maximum group size, candidate pool size, and combinations inspected.
- Health endpoints distinguish liveness from dependency readiness.
- Reconciliation outputs are persisted before a run is marked complete.
