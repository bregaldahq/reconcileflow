from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from reconcileflow.adapters.ingestion import TabularDatasetParser
from reconcileflow.adapters.memory import InMemoryRepository
from reconcileflow.adapters.reporting import XlsxReportBuilder
from reconcileflow.adapters.runtime import DemoAuthorizer
from reconcileflow.application.errors import ConflictError, DatasetValidationError
from reconcileflow.application.models import RuleSetSnapshot
from reconcileflow.application.services import (
    DatasetService,
    ExportService,
    ReviewService,
    RunService,
)
from reconcileflow.domain.models import (
    DatasetSide,
    ManualAction,
    MatchStatus,
    RuleReference,
    RunStatus,
)
from reconcileflow.domain.normalization import CanonicalMapping


class SequentialIds:
    def __init__(self) -> None:
        self.count = 0

    def new(self, prefix: str) -> str:
        self.count += 1
        return f"{prefix}-{self.count}"


@dataclass
class FixedClock:
    current: datetime = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


class RecordingDispatcher:
    def __init__(self) -> None:
        self.run_ids: list[str] = []

    def dispatch_reconciliation(self, run_id: str) -> None:
        self.run_ids.append(run_id)


class FailingOnceDispatcher(RecordingDispatcher):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    def dispatch_reconciliation(self, run_id: str) -> None:
        if not self.failed:
            self.failed = True
            raise RuntimeError("broker unavailable")
        super().dispatch_reconciliation(run_id)


class FailingAuditRepository(InMemoryRepository):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_audit = True

    def add_audit(self, event):
        if self.fail_next_audit:
            self.fail_next_audit = False
            raise RuntimeError("audit store unavailable")
        return super().add_audit(event)


def profile() -> RuleSetSnapshot:
    return RuleSetSnapshot(
        reference=RuleReference("standard", "1"),
        exact_fields=("currency", "amount", "date", "document"),
        amount_tolerance="0.50",
        date_tolerance_days=2,
    )


def upload_and_map(
    service: DatasetService,
    *,
    side: DatasetSide,
    name: str,
    rows: str,
):
    dataset = service.create(
        name=name,
        side=side,
        content_type="text/csv",
        content=rows.encode(),
    )
    return service.map(
        dataset.dataset_id,
        CanonicalMapping(
            amount="amount",
            currency="currency",
            booking_date="date",
            transaction_id="id",
            document="document",
            reference="reference",
        ),
    )


def test_dataset_mapping_collects_row_issues() -> None:
    service = DatasetService(
        InMemoryRepository(), TabularDatasetParser(), SequentialIds(), FixedClock()
    )
    dataset = service.create(
        name="a.csv",
        side=DatasetSide.A,
        content_type="text/csv",
        content=b"id,amount,currency,date\n1,not-money,BRL,2026-01-01\n",
    )
    with pytest.raises(DatasetValidationError) as captured:
        service.map(
            dataset.dataset_id,
            CanonicalMapping("amount", "currency", "date", transaction_id="id"),
        )
    assert captured.value.issues[0].row == 2


def test_dataset_mapping_rejects_missing_columns_and_normalized_duplicate_ids() -> None:
    service = DatasetService(
        InMemoryRepository(), TabularDatasetParser(), SequentialIds(), FixedClock()
    )
    dataset = service.create(
        name="a.csv",
        side=DatasetSide.A,
        content_type="text/csv",
        content=b"id,amount,date\nA-1,10.00,2026-01-01\nA1,20.00,2026-01-02\n",
    )
    with pytest.raises(DatasetValidationError) as missing:
        service.map(
            dataset.dataset_id,
            CanonicalMapping("missing", None, "date", transaction_id="id"),
        )
    assert missing.value.issues[0].code == "missing_mapped_column"

    with pytest.raises(DatasetValidationError) as duplicate:
        service.map(
            dataset.dataset_id,
            CanonicalMapping("amount", None, "date", transaction_id="id"),
        )
    assert duplicate.value.issues[0].code == "duplicate_transaction_id"
    assert duplicate.value.issues[0].row == 3


def test_sync_run_is_completed_and_start_is_idempotent() -> None:
    repository = InMemoryRepository()
    ids = SequentialIds()
    clock = FixedClock()
    datasets = DatasetService(repository, TabularDatasetParser(), ids, clock)
    dataset_a = upload_and_map(
        datasets,
        side=DatasetSide.A,
        name="a.csv",
        rows="id,amount,currency,date,document,reference\nA1,100.00,BRL,2026-01-01,123,REF-A\n",
    )
    dataset_b = upload_and_map(
        datasets,
        side=DatasetSide.B,
        name="b.csv",
        rows="id,amount,currency,date,document,reference\nB1,100.00,BRL,2026-01-01,123,REF-B\n",
    )
    dispatcher = RecordingDispatcher()
    runs = RunService(repository, dispatcher, ids, clock, async_row_threshold=100)
    first = runs.start(
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        profile=profile(),
        idempotency_key="start-1",
        correlation_id="corr-1",
    )
    second = runs.start(
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        profile=profile(),
        idempotency_key="start-1",
        correlation_id="different-correlation",
    )
    assert first == second
    assert first.run.status is RunStatus.COMPLETED
    assert first.decisions[0].status is MatchStatus.MATCHED
    assert dispatcher.run_ids == []


def test_large_run_is_queued_and_worker_execution_is_idempotent() -> None:
    repository = InMemoryRepository()
    ids = SequentialIds()
    clock = FixedClock()
    datasets = DatasetService(repository, TabularDatasetParser(), ids, clock)
    header = "id,amount,currency,date,document,reference\n"
    dataset_a = upload_and_map(
        datasets,
        side=DatasetSide.A,
        name="a.csv",
        rows=header + "A1,100,BRL,2026-01-01,123,REF\n",
    )
    dataset_b = upload_and_map(
        datasets,
        side=DatasetSide.B,
        name="b.csv",
        rows=header + "B1,100,BRL,2026-01-01,123,REF\n",
    )
    dispatcher = RecordingDispatcher()
    runs = RunService(repository, dispatcher, ids, clock, async_row_threshold=1)
    queued = runs.start(
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        profile=profile(),
        idempotency_key="async-1",
        correlation_id="corr-1",
    )
    assert queued.run.status is RunStatus.QUEUED
    assert dispatcher.run_ids == [queued.run.run_id]
    completed = runs.execute(queued.run.run_id)
    retried = runs.execute(queued.run.run_id)
    assert completed == retried
    assert len(completed.decisions) == 1


def test_worker_retry_recovers_a_run_claim_without_duplicate_decisions() -> None:
    repository = InMemoryRepository()
    ids = SequentialIds()
    clock = FixedClock()
    datasets = DatasetService(repository, TabularDatasetParser(), ids, clock)
    header = "id,amount,currency,date,document,reference\n"
    dataset_a = upload_and_map(
        datasets,
        side=DatasetSide.A,
        name="a.csv",
        rows=header + "A1,100,BRL,2026-01-01,123,REF\n",
    )
    dataset_b = upload_and_map(
        datasets,
        side=DatasetSide.B,
        name="b.csv",
        rows=header + "B1,100,BRL,2026-01-01,123,REF\n",
    )
    runs = RunService(repository, RecordingDispatcher(), ids, clock, async_row_threshold=1)
    queued = runs.start(
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        profile=profile(),
        idempotency_key="recover-1",
        correlation_id="corr-1",
    )
    claimed = repository.transition_run(
        queued.run.run_id,
        frozenset({RunStatus.QUEUED}),
        RunStatus.RUNNING,
        clock.now(),
    )
    assert claimed is not None

    completed = runs.execute(queued.run.run_id, recover_running=True)

    assert completed.run.status is RunStatus.COMPLETED
    assert len(completed.decisions) == 1


def test_start_retry_redispatches_a_queued_run_after_broker_failure() -> None:
    repository = InMemoryRepository()
    ids = SequentialIds()
    clock = FixedClock()
    datasets = DatasetService(repository, TabularDatasetParser(), ids, clock)
    header = "id,amount,currency,date,document,reference\n"
    dataset_a = upload_and_map(
        datasets,
        side=DatasetSide.A,
        name="a.csv",
        rows=header + "A1,100,BRL,2026-01-01,123,REF\n",
    )
    dataset_b = upload_and_map(
        datasets,
        side=DatasetSide.B,
        name="b.csv",
        rows=header + "B1,100,BRL,2026-01-01,123,REF\n",
    )
    dispatcher = FailingOnceDispatcher()
    runs = RunService(repository, dispatcher, ids, clock, async_row_threshold=1)
    request = {
        "dataset_a_id": dataset_a.dataset_id,
        "dataset_b_id": dataset_b.dataset_id,
        "profile": profile(),
        "idempotency_key": "dispatch-retry-1",
        "correlation_id": "corr-1",
    }
    with pytest.raises(RuntimeError, match="broker unavailable"):
        runs.start(**request)

    queued = runs.start(**request)

    assert queued.run.status is RunStatus.QUEUED
    assert dispatcher.run_ids == [queued.run.run_id]


def test_review_is_append_only_and_export_is_deterministic() -> None:
    repository = FailingAuditRepository()
    ids = SequentialIds()
    clock = FixedClock()
    datasets = DatasetService(repository, TabularDatasetParser(), ids, clock)
    header = "id,amount,currency,date,document,reference\n"
    dataset_a = upload_and_map(
        datasets,
        side=DatasetSide.A,
        name="a.csv",
        rows=header + "A1,100,BRL,2026-01-01,123,SOURCE\n",
    )
    dataset_b = upload_and_map(
        datasets,
        side=DatasetSide.B,
        name="b.csv",
        rows=(
            header + "B1,100,BRL,2026-01-01,123,TARGET-1\n" + "B2,100,BRL,2026-01-01,123,TARGET-2\n"
        ),
    )
    runs = RunService(repository, RecordingDispatcher(), ids, clock, async_row_threshold=100)
    bundle = runs.start(
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        profile=profile(),
        idempotency_key="ambiguous-1",
        correlation_id="corr",
    )
    decision = next(item for item in bundle.decisions if item.status is MatchStatus.AMBIGUOUS)
    reviews = ReviewService(repository, DemoAuthorizer(), ids, clock)
    review_request = {
        "run_id": bundle.run.run_id,
        "decision_id": decision.decision_id,
        "action": ManualAction.APPROVE,
        "actor_id": "analyst@example.test",
        "reason": "=reviewed evidence",
        "idempotency_key": "review-1",
    }
    with pytest.raises(RuntimeError, match="audit store unavailable"):
        reviews.record(**review_request)
    first = reviews.record(**review_request)
    second = reviews.record(
        run_id=bundle.run.run_id,
        decision_id=decision.decision_id,
        action=ManualAction.APPROVE,
        actor_id="analyst@example.test",
        reason="=reviewed evidence",
        idempotency_key="review-1",
    )
    assert first == second
    with pytest.raises(ConflictError, match="outra revisão"):
        reviews.record(
            run_id=bundle.run.run_id,
            decision_id=decision.decision_id,
            action=ManualAction.REJECT,
            actor_id="analyst@example.test",
            reason="different retry body",
            idempotency_key="review-1",
        )
    assert len(repository.list_reviews(bundle.run.run_id)) == 1
    assert len(repository.list_audit(bundle.run.run_id)) == 1

    exports = ExportService(repository, XlsxReportBuilder(), DemoAuthorizer(), ids, clock)
    export_request = {
        "run_id": bundle.run.run_id,
        "actor_id": "analyst@example.test",
        "idempotency_key": "export-1",
    }
    repository.fail_next_audit = True
    with pytest.raises(RuntimeError, match="audit store unavailable"):
        exports.create(**export_request)
    report = exports.create(**export_request)
    retried = exports.create(
        run_id=bundle.run.run_id,
        actor_id="analyst@example.test",
        idempotency_key="export-1",
    )
    assert report == retried
    assert report.content.startswith(b"PK")
    assert report.fingerprint.sha256
    assert len(repository.list_audit(bundle.run.run_id)) == 2


def test_review_rejects_non_reviewable_decision() -> None:
    repository = InMemoryRepository()
    ids = SequentialIds()
    clock = FixedClock()
    datasets = DatasetService(repository, TabularDatasetParser(), ids, clock)
    header = "id,amount,currency,date,document,reference\n"
    a = upload_and_map(
        datasets,
        side=DatasetSide.A,
        name="a.csv",
        rows=header + "A,10,BRL,2026-01-01,123,R\n",
    )
    b = upload_and_map(
        datasets,
        side=DatasetSide.B,
        name="b.csv",
        rows=header + "B,10,BRL,2026-01-01,123,R\n",
    )
    bundle = RunService(
        repository, RecordingDispatcher(), ids, clock, async_row_threshold=10
    ).start(
        dataset_a_id=a.dataset_id,
        dataset_b_id=b.dataset_id,
        profile=profile(),
        idempotency_key="run",
        correlation_id="corr",
    )
    with pytest.raises(ConflictError, match="somente decisões ambíguas"):
        ReviewService(repository, DemoAuthorizer(), ids, clock).record(
            run_id=bundle.run.run_id,
            decision_id=bundle.decisions[0].decision_id,
            action=ManualAction.APPROVE,
            actor_id="analyst",
            reason="looks right",
            idempotency_key="review",
        )
