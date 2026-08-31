# ADR 0003: PostgreSQL persistence and Redis-backed Celery

Status: Accepted

PostgreSQL stores datasets, mappings, versioned profiles, runs, decisions, participants, reviews, audit events, and export metadata. Redis brokers Celery jobs for large runs. Small demo runs may execute inline through the same application use case.

Database constraints provide idempotency and append-only protection; the worker remains at-least-once and safe to retry. SQLite is used only for fast adapter integration tests, with PostgreSQL exercised by the Compose smoke profile and CI service.
