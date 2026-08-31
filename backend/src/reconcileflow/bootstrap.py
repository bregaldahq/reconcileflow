"""Composition root; the only place concrete adapters are assembled."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import create_engine

from reconcileflow.adapters.async_jobs import CeleryDispatcher
from reconcileflow.adapters.database import SqlAlchemyRepository, create_schema
from reconcileflow.adapters.ingestion import IngestionLimits, TabularDatasetParser
from reconcileflow.adapters.memory import InMemoryRepository
from reconcileflow.adapters.reporting import XlsxReportBuilder
from reconcileflow.adapters.runtime import (
    DemoAuthorizer,
    NoopDispatcher,
    SystemClock,
    UuidGenerator,
)
from reconcileflow.application.models import RuleSetSnapshot
from reconcileflow.application.ports import Repository
from reconcileflow.application.services import (
    DatasetService,
    ExportService,
    ReviewService,
    RunService,
)
from reconcileflow.domain.models import RuleReference
from reconcileflow.settings import Settings

DEFAULT_PROFILE = RuleSetSnapshot(
    reference=RuleReference("standard", "1"),
    exact_fields=("currency", "amount", "date", "document", "reference"),
    amount_tolerance="0.50",
    date_tolerance_days=2,
    split_enabled=True,
    max_group_size=4,
    max_candidate_pool=20,
    max_combinations=5000,
)


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    repository: Repository
    datasets: DatasetService
    runs: RunService
    reviews: ReviewService
    exports: ExportService
    profiles: tuple[RuleSetSnapshot, ...]


def build_container(settings: Settings | None = None) -> Container:
    configured = settings or Settings()
    if configured.repository_backend == "sqlalchemy":
        engine = create_engine(configured.database_url, pool_pre_ping=True)
        if configured.environment != "production" and configured.database_url.startswith("sqlite"):
            create_schema(engine)
        repository: Repository = SqlAlchemyRepository(engine)
    else:
        repository = InMemoryRepository()
    clock = SystemClock()
    ids = UuidGenerator()
    parser = TabularDatasetParser(
        IngestionLimits(
            max_bytes=configured.max_upload_bytes,
            max_rows=configured.max_upload_rows,
        )
    )
    dispatcher = (
        CeleryDispatcher(configured.redis_url) if configured.async_enabled else NoopDispatcher()
    )
    async_row_threshold = (
        configured.async_row_threshold
        if configured.async_enabled
        else configured.max_upload_rows * 2 + 1
    )
    return Container(
        settings=configured,
        repository=repository,
        datasets=DatasetService(repository, parser, ids, clock),
        runs=RunService(
            repository,
            dispatcher,
            ids,
            clock,
            async_row_threshold=async_row_threshold,
        ),
        reviews=ReviewService(repository, DemoAuthorizer(), ids, clock),
        exports=ExportService(repository, XlsxReportBuilder(), DemoAuthorizer(), ids, clock),
        profiles=(DEFAULT_PROFILE,),
    )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build_container()
