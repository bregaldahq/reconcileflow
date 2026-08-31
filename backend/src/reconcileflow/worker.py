"""Celery worker entry point."""

from __future__ import annotations

import time

import structlog
from celery import Task
from sqlalchemy.exc import OperationalError

from reconcileflow.adapters.async_jobs import create_celery_app
from reconcileflow.application.errors import PermanentApplicationError, RetryableApplicationError
from reconcileflow.bootstrap import get_container
from reconcileflow.domain.errors import DomainError
from reconcileflow.observability import configure_observability, log_run_outcome
from reconcileflow.settings import Settings

settings = Settings()
configure_observability(log_level=settings.log_level, otel_enabled=settings.otel_enabled)
celery_app = create_celery_app(settings.redis_url)


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="reconcileflow.execute_reconciliation",
    autoretry_for=(RetryableApplicationError, OperationalError),
    dont_autoretry_for=(PermanentApplicationError, DomainError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=False,
    max_retries=5,
)
def execute_reconciliation(task: Task, run_id: str) -> str:
    started = time.perf_counter()
    structlog.get_logger("reconcileflow.worker").info("reconciliation_job_started", run_id=run_id)
    recovering = bool(getattr(task.request, "retries", 0))
    bundle = get_container().runs.execute(run_id, recover_running=recovering)
    log_run_outcome(bundle, duration_ms=int((time.perf_counter() - started) * 1000))
    return bundle.run.status.value
