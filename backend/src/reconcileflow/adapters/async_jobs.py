"""Redis-backed Celery dispatch adapter."""

from __future__ import annotations

from celery import Celery


class CeleryDispatcher:
    def __init__(self, broker_url: str) -> None:
        self._client = Celery("reconcileflow-dispatch", broker=broker_url)

    def dispatch_reconciliation(self, run_id: str) -> None:
        self._client.send_task(
            "reconcileflow.execute_reconciliation",
            args=(run_id,),
            task_id=f"reconcileflow-run-{run_id}",
        )


def create_celery_app(redis_url: str) -> Celery:
    app = Celery("reconcileflow", broker=redis_url, backend=redis_url)
    app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_serializer="json",
        accept_content=("json",),
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_prefetch_multiplier=1,
    )
    return app
