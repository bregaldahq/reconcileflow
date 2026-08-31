"""Ports owned by the application layer and implemented by adapters."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from reconcileflow.application.models import (
    AuditEvent,
    DatasetRecord,
    ExportArtifact,
    ManualReviewEvent,
    ParsedDataset,
    ReportPayload,
    RuleSetSnapshot,
    RunBundle,
)
from reconcileflow.domain.models import ReconciliationResult, RunStatus


class DatasetParser(Protocol):
    def parse(self, *, filename: str, content_type: str, content: bytes) -> ParsedDataset: ...


class Repository(Protocol):
    def add_dataset(self, dataset: DatasetRecord) -> DatasetRecord: ...

    def get_dataset(self, dataset_id: str) -> DatasetRecord | None: ...

    def list_datasets(self) -> tuple[DatasetRecord, ...]: ...

    def save_mapping(self, dataset: DatasetRecord) -> DatasetRecord: ...

    def add_rule_set(self, profile: RuleSetSnapshot) -> RuleSetSnapshot: ...

    def get_rule_set(self, rule_id: str, version: str) -> RuleSetSnapshot | None: ...

    def add_run(self, bundle: RunBundle) -> RunBundle: ...

    def find_run_by_idempotency_key(self, key: str) -> RunBundle | None: ...

    def get_run(self, run_id: str) -> RunBundle | None: ...

    def list_runs(self) -> tuple[RunBundle, ...]: ...

    def transition_run(
        self,
        run_id: str,
        expected: frozenset[RunStatus],
        status: RunStatus,
        changed_at: datetime,
        *,
        error_code: str | None = None,
    ) -> RunBundle | None: ...

    def save_result(self, run_id: str, result: ReconciliationResult) -> RunBundle: ...

    def add_review(self, event: ManualReviewEvent) -> ManualReviewEvent: ...

    def find_review_by_idempotency_key(self, key: str) -> ManualReviewEvent | None: ...

    def list_reviews(self, run_id: str) -> tuple[ManualReviewEvent, ...]: ...

    def add_audit(self, event: AuditEvent) -> AuditEvent: ...

    def list_audit(self, run_id: str) -> tuple[AuditEvent, ...]: ...

    def add_export(self, artifact: ExportArtifact) -> ExportArtifact: ...

    def find_export_by_idempotency_key(self, key: str) -> ExportArtifact | None: ...


class JobDispatcher(Protocol):
    def dispatch_reconciliation(self, run_id: str) -> None: ...


class ReportBuilder(Protocol):
    def build(self, payload: ReportPayload) -> bytes: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self, prefix: str) -> str: ...


class Authorizer(Protocol):
    def require(self, actor_id: str, permission: str) -> None: ...


ExecuteCallback = Callable[[str], RunBundle]
