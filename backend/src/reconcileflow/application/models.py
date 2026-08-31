"""Application records crossing use-case and adapter boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from reconcileflow.domain.models import (
    CanonicalTransaction,
    DatasetFingerprint,
    DatasetSide,
    ManualAction,
    ReconciliationDecision,
    ReconciliationRun,
    RuleReference,
)
from reconcileflow.domain.normalization import CanonicalMapping


@dataclass(frozen=True, slots=True)
class ParsedDataset:
    fingerprint: DatasetFingerprint
    headers: tuple[str, ...]
    rows: tuple[dict[str, object], ...]
    byte_size: int


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    dataset_id: str
    name: str
    side: DatasetSide
    content_type: str
    fingerprint: DatasetFingerprint
    headers: tuple[str, ...]
    rows: tuple[dict[str, object], ...]
    byte_size: int
    created_at: datetime
    mapping: CanonicalMapping | None = None
    transactions: tuple[CanonicalTransaction, ...] = ()

    @property
    def is_mapped(self) -> bool:
        return self.mapping is not None and bool(self.transactions)


@dataclass(frozen=True, slots=True)
class RuleSetSnapshot:
    reference: RuleReference
    exact_fields: tuple[str, ...]
    amount_tolerance: str
    date_tolerance_days: int
    split_enabled: bool = True
    max_group_size: int = 4
    max_candidate_pool: int = 20
    max_combinations: int = 5000


@dataclass(frozen=True, slots=True)
class RunBundle:
    run: ReconciliationRun
    dataset_a_id: str
    dataset_b_id: str
    profile: RuleSetSnapshot
    decisions: tuple[ReconciliationDecision, ...] = ()
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class ManualReviewEvent:
    event_id: str
    run_id: str
    decision_id: str
    action: ManualAction
    actor_id: str
    reason: str
    idempotency_key: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    run_id: str
    event_type: str
    actor_id: str
    detail: str
    idempotency_key: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReportPayload:
    run: ReconciliationRun
    decisions: tuple[ReconciliationDecision, ...]
    transactions: tuple[CanonicalTransaction, ...]
    reviews: tuple[ManualReviewEvent, ...]


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    export_id: str
    run_id: str
    filename: str
    content_type: str
    content: bytes
    fingerprint: DatasetFingerprint
    idempotency_key: str
    created_at: datetime
