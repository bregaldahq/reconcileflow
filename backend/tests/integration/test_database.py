from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from alembic import command
from reconcileflow.adapters.database import SqlAlchemyRepository, create_schema
from reconcileflow.adapters.ingestion import TabularDatasetParser
from reconcileflow.adapters.reporting import XlsxReportBuilder
from reconcileflow.adapters.runtime import DemoAuthorizer
from reconcileflow.application.errors import ConflictError
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


class Ids:
    def __init__(self) -> None:
        self.value = 0

    def new(self, prefix: str) -> str:
        self.value += 1
        return f"{prefix}-{self.value}"


@dataclass
class Clock:
    value: datetime = datetime(2026, 2, 1, tzinfo=UTC)

    def now(self) -> datetime:
        current = self.value
        self.value += timedelta(seconds=1)
        return current


class Dispatcher:
    def __init__(self) -> None:
        self.runs: list[str] = []

    def dispatch_reconciliation(self, run_id: str) -> None:
        self.runs.append(run_id)


@pytest.fixture
def engine() -> Engine:
    database = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(database, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    create_schema(database)
    yield database
    database.dispose()


def mapped_dataset(service: DatasetService, side: DatasetSide, filename: str, body: str):
    dataset = service.create(
        name=filename,
        side=side,
        content_type="text/csv",
        content=body.encode(),
    )
    return service.map(
        dataset.dataset_id,
        CanonicalMapping(
            "amount",
            "currency",
            "date",
            transaction_id="id",
            document="document",
            reference="reference",
        ),
    )


@pytest.mark.integration
def test_sql_repository_supports_full_ambiguous_review_export_flow(engine: Engine) -> None:
    repository = SqlAlchemyRepository(engine)
    ids = Ids()
    clock = Clock()
    datasets = DatasetService(repository, TabularDatasetParser(), ids, clock)
    header = "id,amount,currency,date,document,reference\n"
    dataset_a = mapped_dataset(
        datasets,
        DatasetSide.A,
        "a.csv",
        header + "A1,100.00,BRL,2026-02-01,DOC,SOURCE\n",
    )
    dataset_b = mapped_dataset(
        datasets,
        DatasetSide.B,
        "b.csv",
        header
        + "B1,100.00,BRL,2026-02-01,DOC,TARGET-1\n"
        + "B2,100.00,BRL,2026-02-01,DOC,TARGET-2\n",
    )
    assert len(repository.list_datasets()) == 2
    with pytest.raises(ConflictError, match="não pode ser alterada"):
        datasets.map(
            dataset_a.dataset_id,
            CanonicalMapping(
                "amount", "currency", "date", transaction_id="id", document="document"
            ),
        )

    profile = RuleSetSnapshot(
        RuleReference("standard", "1"),
        ("currency", "amount", "date", "document"),
        "0.50",
        2,
    )
    dispatcher = Dispatcher()
    runs = RunService(repository, dispatcher, ids, clock, async_row_threshold=1)
    queued = runs.start(
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        profile=profile,
        idempotency_key="run-key",
        correlation_id="correlation",
    )
    assert queued.run.status is RunStatus.QUEUED
    completed = runs.execute(queued.run.run_id)
    assert completed.run.status is RunStatus.COMPLETED
    assert completed == runs.execute(queued.run.run_id)
    assert completed == repository.find_run_by_idempotency_key("run-key")
    decision = next(item for item in completed.decisions if item.status is MatchStatus.AMBIGUOUS)

    review_service = ReviewService(repository, DemoAuthorizer(), ids, clock)
    review = review_service.record(
        run_id=completed.run.run_id,
        decision_id=decision.decision_id,
        action=ManualAction.APPROVE,
        actor_id="analyst",
        reason="evidence checked",
        idempotency_key="review-key",
    )
    assert review == repository.find_review_by_idempotency_key("review-key")
    assert len(repository.list_audit(completed.run.run_id)) == 1

    export_service = ExportService(repository, XlsxReportBuilder(), DemoAuthorizer(), ids, clock)
    artifact = export_service.create(
        run_id=completed.run.run_id,
        actor_id="analyst",
        idempotency_key="export-key",
    )
    assert artifact == repository.find_export_by_idempotency_key("export-key")
    assert artifact.content.startswith(b"PK")
    assert len(repository.list_runs()) == 1


@pytest.mark.integration
def test_alembic_initial_migration_upgrades_clean_database(tmp_path: Path) -> None:
    root = Path(__file__).parents[3]
    database_path = tmp_path / "migration.db"
    config = Config(str(root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    database = create_engine(f"sqlite:///{database_path.as_posix()}")
    tables = set(inspect(database).get_table_names())
    assert {
        "datasets",
        "mapping_profiles",
        "rule_sets",
        "reconciliation_runs",
        "reconciliation_decisions",
        "match_participants",
        "audit_events",
        "manual_reviews",
        "exports",
    } <= tables
    run_columns = {
        item["name"]: item for item in inspect(database).get_columns("reconciliation_runs")
    }
    assert run_columns["dataset_a_id"]["nullable"] is False
    assert run_columns["dataset_b_id"]["nullable"] is False
    run_checks = {
        item["name"] for item in inspect(database).get_check_constraints("reconciliation_runs")
    }
    assert "ck_run_status" in run_checks
    database.dispose()
