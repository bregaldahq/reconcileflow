# ADR 0001: Modular monolith with inward dependencies

Status: Accepted

ReconcileFlow starts as a modular monolith. The pure domain contains canonical models and matching. Application use cases depend on ports. FastAPI, SQLAlchemy, Celery, file parsing, and reporting are adapters.

This keeps deployment understandable while preserving replaceable infrastructure and testable financial logic. Separate services would add operational cost without a demonstrated scaling boundary.
