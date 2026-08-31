"""Structured, privacy-conscious operational signals."""

from __future__ import annotations

import contextvars
import logging
from collections import Counter

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from structlog.typing import EventDict, WrappedLogger

from reconcileflow.application.models import RunBundle

correlation_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="unknown"
)


def _add_correlation_id(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    del logger, method_name
    event_dict["correlation_id"] = correlation_id_context.get()
    return event_dict


def configure_observability(*, log_level: str, otel_enabled: bool) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO), format="%(message)s"
    )
    structlog.configure(
        processors=[
            _add_correlation_id,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    if otel_enabled and not isinstance(trace.get_tracer_provider(), TracerProvider):
        trace.set_tracer_provider(TracerProvider())


def log_run_outcome(bundle: RunBundle, *, duration_ms: int) -> None:
    counts = Counter(item.status.value for item in bundle.decisions)
    structlog.get_logger("reconcileflow.run").info(
        "reconciliation_run_finished",
        run_id=bundle.run.run_id,
        dataset_a_fingerprint=bundle.run.dataset_a.short(),
        dataset_b_fingerprint=bundle.run.dataset_b.short(),
        rule_set=f"{bundle.run.rule_set.rule_id}@{bundle.run.rule_set.version}",
        status=bundle.run.status.value,
        duration_ms=duration_ms,
        counts=dict(sorted(counts.items())),
    )
