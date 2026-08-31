"""Thread-safe in-memory adapter used by tests and zero-dependency demos."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from threading import RLock

from reconcileflow.application.errors import ConflictError, NotFoundError
from reconcileflow.application.models import (
    AuditEvent,
    DatasetRecord,
    ExportArtifact,
    ManualReviewEvent,
    RuleSetSnapshot,
    RunBundle,
)
from reconcileflow.domain.models import ReconciliationResult, RunStatus


class InMemoryRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._datasets: dict[str, DatasetRecord] = {}
        self._profiles: dict[tuple[str, str], RuleSetSnapshot] = {}
        self._runs: dict[str, RunBundle] = {}
        self._run_keys: dict[str, str] = {}
        self._reviews: dict[str, ManualReviewEvent] = {}
        self._review_keys: dict[str, str] = {}
        self._audits: dict[str, AuditEvent] = {}
        self._exports: dict[str, ExportArtifact] = {}
        self._export_keys: dict[str, str] = {}

    def add_dataset(self, dataset: DatasetRecord) -> DatasetRecord:
        with self._lock:
            if dataset.dataset_id in self._datasets:
                raise ConflictError("o identificador da fonte de dados já existe")
            self._datasets[dataset.dataset_id] = dataset
            return dataset

    def get_dataset(self, dataset_id: str) -> DatasetRecord | None:
        with self._lock:
            return self._datasets.get(dataset_id)

    def list_datasets(self) -> tuple[DatasetRecord, ...]:
        with self._lock:
            return tuple(
                sorted(self._datasets.values(), key=lambda item: (item.created_at, item.dataset_id))
            )

    def save_mapping(self, dataset: DatasetRecord) -> DatasetRecord:
        with self._lock:
            existing = self._datasets.get(dataset.dataset_id)
            if existing is None:
                raise NotFoundError("a fonte de dados não existe")
            if existing.mapping is not None:
                if existing == dataset:
                    return existing
                raise ConflictError("uma revisão mapeada da fonte de dados não pode ser alterada")
            self._datasets[dataset.dataset_id] = dataset
            return dataset

    def add_rule_set(self, profile: RuleSetSnapshot) -> RuleSetSnapshot:
        key = (profile.reference.rule_id, profile.reference.version)
        with self._lock:
            existing = self._profiles.get(key)
            if existing is not None and existing != profile:
                raise ConflictError("uma versão de regra não pode ser alterada")
            self._profiles[key] = profile
            return profile

    def get_rule_set(self, rule_id: str, version: str) -> RuleSetSnapshot | None:
        with self._lock:
            return self._profiles.get((rule_id, version))

    def add_run(self, bundle: RunBundle) -> RunBundle:
        with self._lock:
            existing_id = self._run_keys.get(bundle.run.idempotency_key)
            if existing_id is not None:
                return self._runs[existing_id]
            if bundle.run.run_id in self._runs:
                raise ConflictError("o identificador da execução já existe")
            self._runs[bundle.run.run_id] = bundle
            self._run_keys[bundle.run.idempotency_key] = bundle.run.run_id
            return bundle

    def find_run_by_idempotency_key(self, key: str) -> RunBundle | None:
        with self._lock:
            run_id = self._run_keys.get(key)
            return self._runs.get(run_id) if run_id is not None else None

    def get_run(self, run_id: str) -> RunBundle | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self) -> tuple[RunBundle, ...]:
        with self._lock:
            return tuple(
                sorted(
                    self._runs.values(),
                    key=lambda item: (item.run.created_at, item.run.run_id),
                    reverse=True,
                )
            )

    def transition_run(
        self,
        run_id: str,
        expected: frozenset[RunStatus],
        status: RunStatus,
        changed_at: datetime,
        *,
        error_code: str | None = None,
    ) -> RunBundle | None:
        with self._lock:
            bundle = self._runs.get(run_id)
            if bundle is None:
                raise NotFoundError("a execução não existe")
            if bundle.run.status not in expected:
                return None
            changed = bundle.run.transition(status, at=changed_at)
            updated = replace(bundle, run=changed, error_code=error_code)
            self._runs[run_id] = updated
            return updated

    def save_result(self, run_id: str, result: ReconciliationResult) -> RunBundle:
        with self._lock:
            bundle = self._runs.get(run_id)
            if bundle is None:
                raise NotFoundError("a execução não existe")
            if bundle.run.status is not RunStatus.RUNNING:
                raise ConflictError(
                    "os resultados só podem ser salvos durante uma execução em andamento"
                )
            if bundle.decisions and bundle.decisions != result.decisions:
                raise ConflictError("as decisões da execução não podem ser alteradas")
            updated = replace(bundle, decisions=result.decisions)
            self._runs[run_id] = updated
            return updated

    def add_review(self, event: ManualReviewEvent) -> ManualReviewEvent:
        with self._lock:
            existing_id = self._review_keys.get(event.idempotency_key)
            if existing_id is not None:
                return self._reviews[existing_id]
            self._reviews[event.event_id] = event
            self._review_keys[event.idempotency_key] = event.event_id
            return event

    def find_review_by_idempotency_key(self, key: str) -> ManualReviewEvent | None:
        with self._lock:
            event_id = self._review_keys.get(key)
            return self._reviews.get(event_id) if event_id is not None else None

    def list_reviews(self, run_id: str) -> tuple[ManualReviewEvent, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (item for item in self._reviews.values() if item.run_id == run_id),
                    key=lambda item: (item.created_at, item.event_id),
                )
            )

    def add_audit(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            if any(item.idempotency_key == event.idempotency_key for item in self._audits.values()):
                return next(
                    item
                    for item in self._audits.values()
                    if item.idempotency_key == event.idempotency_key
                )
            self._audits[event.event_id] = event
            return event

    def list_audit(self, run_id: str) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (item for item in self._audits.values() if item.run_id == run_id),
                    key=lambda item: (item.created_at, item.event_id),
                )
            )

    def add_export(self, artifact: ExportArtifact) -> ExportArtifact:
        with self._lock:
            existing_id = self._export_keys.get(artifact.idempotency_key)
            if existing_id is not None:
                return self._exports[existing_id]
            self._exports[artifact.export_id] = artifact
            self._export_keys[artifact.idempotency_key] = artifact.export_id
            return artifact

    def find_export_by_idempotency_key(self, key: str) -> ExportArtifact | None:
        with self._lock:
            export_id = self._export_keys.get(key)
            return self._exports.get(export_id) if export_id is not None else None
