"""SQLAlchemy persistence adapter for PostgreSQL and isolated SQLite tests."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from reconcileflow.application.errors import ConflictError, NotFoundError
from reconcileflow.application.models import (
    AuditEvent,
    DatasetRecord,
    ExportArtifact,
    ManualReviewEvent,
    RuleSetSnapshot,
    RunBundle,
)
from reconcileflow.domain.models import (
    CanonicalTransaction,
    DatasetFingerprint,
    DatasetSide,
    ManualAction,
    MatchExplanation,
    MatchStatus,
    Money,
    ReconciliationDecision,
    ReconciliationResult,
    ReconciliationRun,
    RuleReference,
    RunStatus,
)
from reconcileflow.domain.normalization import NORMALIZATION_VERSION, CanonicalMapping


class Base(DeclarativeBase):
    pass


class DatasetModel(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    side: Mapped[str] = mapped_column(String(1))
    content_type: Mapped[str] = mapped_column(String(160))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    headers: Mapped[list[str]] = mapped_column(JSON)
    rows: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    byte_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MappingProfileModel(Base):
    __tablename__ = "mapping_profiles"

    mapping_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.dataset_id", ondelete="CASCADE"), unique=True
    )
    normalization_version: Mapped[str] = mapped_column(String(32))
    config: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CanonicalTransactionModel(Base):
    __tablename__ = "canonical_transactions"

    transaction_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.dataset_id", ondelete="CASCADE"), index=True
    )
    side: Mapped[str] = mapped_column(String(1))
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 2))
    currency: Mapped[str] = mapped_column(String(3))
    booking_date: Mapped[date] = mapped_column(Date)
    source_record_id: Mapped[str] = mapped_column(String(255))
    document: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    __table_args__ = (
        UniqueConstraint("dataset_id", "source_record_id", name="uq_transaction_source_record"),
    )


class RuleSetModel(Base):
    __tablename__ = "rule_sets"

    rule_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[str] = mapped_column(String(40), primary_key=True)
    exact_fields: Mapped[list[str]] = mapped_column(JSON)
    amount_tolerance: Mapped[Decimal] = mapped_column(Numeric(38, 2))
    date_tolerance_days: Mapped[int] = mapped_column(Integer)
    split_enabled: Mapped[bool]
    max_group_size: Mapped[int] = mapped_column(Integer)
    max_candidate_pool: Mapped[int] = mapped_column(Integer)
    max_combinations: Mapped[int] = mapped_column(Integer)


class RunModel(Base):
    __tablename__ = "reconciliation_runs"

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    dataset_a_id: Mapped[str] = mapped_column(ForeignKey("datasets.dataset_id"))
    dataset_b_id: Mapped[str] = mapped_column(ForeignKey("datasets.dataset_id"))
    dataset_a_fingerprint: Mapped[str] = mapped_column(String(64))
    dataset_b_fingerprint: Mapped[str] = mapped_column(String(64))
    rule_id: Mapped[str] = mapped_column(String(80))
    rule_version: Mapped[str] = mapped_column(String(40))
    normalization_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(100), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ("rule_id", "rule_version"),
            ("rule_sets.rule_id", "rule_sets.version"),
        ),
        UniqueConstraint("run_id", "dataset_a_id", "dataset_b_id", name="uq_run_datasets"),
    )


class DecisionModel(Base):
    __tablename__ = "reconciliation_decisions"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("reconciliation_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    decision_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    rule_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[str]] = mapped_column(JSON)


class MatchParticipantModel(Base):
    __tablename__ = "match_participants"

    participant_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80))
    decision_id: Mapped[str] = mapped_column(String(80))
    transaction_id: Mapped[str] = mapped_column(ForeignKey("canonical_transactions.transaction_id"))
    dataset_side: Mapped[str] = mapped_column(String(1))
    __table_args__ = (
        ForeignKeyConstraint(
            ("run_id", "decision_id"),
            (
                "reconciliation_decisions.run_id",
                "reconciliation_decisions.decision_id",
            ),
            ondelete="CASCADE",
        ),
        UniqueConstraint("run_id", "transaction_id", name="uq_run_transaction_participation"),
    )


class ManualReviewModel(Base):
    __tablename__ = "manual_reviews"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80))
    decision_id: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        ForeignKeyConstraint(
            ("run_id", "decision_id"),
            (
                "reconciliation_decisions.run_id",
                "reconciliation_decisions.decision_id",
            ),
        ),
    )


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("reconciliation_runs.run_id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    actor_id: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExportModel(Base):
    __tablename__ = "exports"

    export_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("reconciliation_runs.run_id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(160))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    fingerprint: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _mapping_payload(mapping: CanonicalMapping) -> dict[str, object]:
    return {
        "amount": mapping.amount,
        "currency": mapping.currency,
        "booking_date": mapping.booking_date,
        "transaction_id": mapping.transaction_id,
        "source_record_id": mapping.source_record_id,
        "document": mapping.document,
        "reference": mapping.reference,
        "default_currency": mapping.default_currency,
    }


def _mapping_from_payload(payload: dict[str, object]) -> CanonicalMapping:
    return CanonicalMapping(
        amount=cast(str, payload["amount"]),
        currency=cast(str | None, payload["currency"]),
        booking_date=cast(str, payload["booking_date"]),
        transaction_id=cast(str | None, payload["transaction_id"]),
        source_record_id=cast(str | None, payload["source_record_id"]),
        document=cast(str | None, payload["document"]),
        reference=cast(str | None, payload["reference"]),
        default_currency=cast(str, payload["default_currency"]),
    )


def _transaction(model: CanonicalTransactionModel) -> CanonicalTransaction:
    return CanonicalTransaction(
        transaction_id=model.transaction_id,
        dataset_id=model.dataset_id,
        side=DatasetSide(model.side),
        money=Money(model.amount, model.currency),
        booking_date=model.booking_date,
        source_record_id=model.source_record_id,
        document=model.document,
        reference=model.reference,
    )


def _profile(model: RuleSetModel) -> RuleSetSnapshot:
    return RuleSetSnapshot(
        reference=RuleReference(model.rule_id, model.version),
        exact_fields=tuple(model.exact_fields),
        amount_tolerance=str(model.amount_tolerance),
        date_tolerance_days=model.date_tolerance_days,
        split_enabled=model.split_enabled,
        max_group_size=model.max_group_size,
        max_candidate_pool=model.max_candidate_pool,
        max_combinations=model.max_combinations,
    )


class SqlAlchemyRepository:
    def __init__(self, engine: Engine) -> None:
        self._sessions = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        with self._sessions.begin() as session:
            yield session

    def add_dataset(self, dataset: DatasetRecord) -> DatasetRecord:
        with self._session() as session:
            if session.get(DatasetModel, dataset.dataset_id) is not None:
                raise ConflictError("o identificador da fonte de dados já existe")
            session.add(
                DatasetModel(
                    dataset_id=dataset.dataset_id,
                    name=dataset.name,
                    side=dataset.side.value,
                    content_type=dataset.content_type,
                    fingerprint=dataset.fingerprint.sha256,
                    headers=list(dataset.headers),
                    rows=list(dataset.rows),
                    byte_size=dataset.byte_size,
                    created_at=dataset.created_at,
                )
            )
        return dataset

    def get_dataset(self, dataset_id: str) -> DatasetRecord | None:
        with self._session() as session:
            model = session.get(DatasetModel, dataset_id)
            return self._dataset(session, model) if model is not None else None

    def list_datasets(self) -> tuple[DatasetRecord, ...]:
        with self._session() as session:
            models = session.scalars(
                select(DatasetModel).order_by(DatasetModel.created_at, DatasetModel.dataset_id)
            ).all()
            return tuple(self._dataset(session, model) for model in models)

    def _dataset(self, session: Session, model: DatasetModel) -> DatasetRecord:
        mapping_model = session.scalar(
            select(MappingProfileModel).where(MappingProfileModel.dataset_id == model.dataset_id)
        )
        transaction_models = session.scalars(
            select(CanonicalTransactionModel)
            .where(CanonicalTransactionModel.dataset_id == model.dataset_id)
            .order_by(CanonicalTransactionModel.transaction_id)
        ).all()
        return DatasetRecord(
            dataset_id=model.dataset_id,
            name=model.name,
            side=DatasetSide(model.side),
            content_type=model.content_type,
            fingerprint=DatasetFingerprint(model.fingerprint),
            headers=tuple(model.headers),
            rows=tuple(dict(row) for row in model.rows),
            byte_size=model.byte_size,
            created_at=_aware(model.created_at),
            mapping=(
                _mapping_from_payload(mapping_model.config) if mapping_model is not None else None
            ),
            transactions=tuple(_transaction(item) for item in transaction_models),
        )

    def save_mapping(self, dataset: DatasetRecord) -> DatasetRecord:
        if dataset.mapping is None:
            raise ConflictError("o mapeamento é obrigatório")
        with self._session() as session:
            if session.get(DatasetModel, dataset.dataset_id) is None:
                raise NotFoundError("a fonte de dados não existe")
            existing = session.scalar(
                select(MappingProfileModel).where(
                    MappingProfileModel.dataset_id == dataset.dataset_id
                )
            )
            if existing is not None:
                stored = self._dataset(
                    session, cast(DatasetModel, session.get(DatasetModel, dataset.dataset_id))
                )
                if stored == dataset:
                    return stored
                raise ConflictError("uma revisão mapeada da fonte de dados não pode ser alterada")
            session.add(
                MappingProfileModel(
                    dataset_id=dataset.dataset_id,
                    normalization_version=NORMALIZATION_VERSION,
                    config=_mapping_payload(dataset.mapping),
                    created_at=dataset.created_at,
                )
            )
            session.add_all(
                [
                    CanonicalTransactionModel(
                        transaction_id=item.transaction_id,
                        dataset_id=item.dataset_id,
                        side=item.side.value,
                        amount=item.money.amount,
                        currency=item.money.currency,
                        booking_date=item.booking_date,
                        source_record_id=item.source_record_id,
                        document=item.document,
                        reference=item.reference,
                    )
                    for item in dataset.transactions
                ]
            )
        return dataset

    def add_rule_set(self, profile: RuleSetSnapshot) -> RuleSetSnapshot:
        key = (profile.reference.rule_id, profile.reference.version)
        with self._session() as session:
            existing = session.get(RuleSetModel, key)
            if existing is not None:
                if _profile(existing) != profile:
                    raise ConflictError("uma versão de regra não pode ser alterada")
                return profile
            session.add(
                RuleSetModel(
                    rule_id=profile.reference.rule_id,
                    version=profile.reference.version,
                    exact_fields=list(profile.exact_fields),
                    amount_tolerance=Decimal(profile.amount_tolerance),
                    date_tolerance_days=profile.date_tolerance_days,
                    split_enabled=profile.split_enabled,
                    max_group_size=profile.max_group_size,
                    max_candidate_pool=profile.max_candidate_pool,
                    max_combinations=profile.max_combinations,
                )
            )
        return profile

    def get_rule_set(self, rule_id: str, version: str) -> RuleSetSnapshot | None:
        with self._session() as session:
            model = session.get(RuleSetModel, (rule_id, version))
            return _profile(model) if model is not None else None

    def add_run(self, bundle: RunBundle) -> RunBundle:
        with self._session() as session:
            existing = session.scalar(
                select(RunModel).where(RunModel.idempotency_key == bundle.run.idempotency_key)
            )
            if existing is not None:
                return self._bundle(session, existing)
            session.add(
                RunModel(
                    run_id=bundle.run.run_id,
                    dataset_a_id=bundle.dataset_a_id,
                    dataset_b_id=bundle.dataset_b_id,
                    dataset_a_fingerprint=bundle.run.dataset_a.sha256,
                    dataset_b_fingerprint=bundle.run.dataset_b.sha256,
                    rule_id=bundle.run.rule_set.rule_id,
                    rule_version=bundle.run.rule_set.version,
                    normalization_version=bundle.run.normalization_version,
                    status=bundle.run.status.value,
                    created_at=bundle.run.created_at,
                    updated_at=bundle.run.updated_at,
                    correlation_id=bundle.run.correlation_id,
                    idempotency_key=bundle.run.idempotency_key,
                    error_code=bundle.error_code,
                )
            )
        return bundle

    def find_run_by_idempotency_key(self, key: str) -> RunBundle | None:
        with self._session() as session:
            model = session.scalar(select(RunModel).where(RunModel.idempotency_key == key))
            return self._bundle(session, model) if model is not None else None

    def get_run(self, run_id: str) -> RunBundle | None:
        with self._session() as session:
            model = session.get(RunModel, run_id)
            return self._bundle(session, model) if model is not None else None

    def list_runs(self) -> tuple[RunBundle, ...]:
        with self._session() as session:
            models = session.scalars(
                select(RunModel).order_by(RunModel.created_at.desc(), RunModel.run_id)
            ).all()
            return tuple(self._bundle(session, model) for model in models)

    def _bundle(self, session: Session, model: RunModel) -> RunBundle:
        profile_model = session.get(RuleSetModel, (model.rule_id, model.rule_version))
        if profile_model is None:
            raise NotFoundError("o retrato das regras da execução não está disponível")
        decision_models = session.scalars(
            select(DecisionModel)
            .where(DecisionModel.run_id == model.run_id)
            .order_by(DecisionModel.decision_id)
        ).all()
        decisions = tuple(self._decision(session, item) for item in decision_models)
        run = ReconciliationRun(
            run_id=model.run_id,
            dataset_a=DatasetFingerprint(model.dataset_a_fingerprint),
            dataset_b=DatasetFingerprint(model.dataset_b_fingerprint),
            rule_set=RuleReference(model.rule_id, model.rule_version),
            normalization_version=model.normalization_version,
            status=RunStatus(model.status),
            created_at=_aware(model.created_at),
            updated_at=_aware(model.updated_at),
            correlation_id=model.correlation_id,
            idempotency_key=model.idempotency_key,
        )
        return RunBundle(
            run,
            model.dataset_a_id,
            model.dataset_b_id,
            _profile(profile_model),
            decisions,
            model.error_code,
        )

    def _decision(self, session: Session, model: DecisionModel) -> ReconciliationDecision:
        participants = session.scalars(
            select(MatchParticipantModel)
            .where(
                MatchParticipantModel.run_id == model.run_id,
                MatchParticipantModel.decision_id == model.decision_id,
            )
            .order_by(MatchParticipantModel.transaction_id)
        ).all()
        source_ids = tuple(
            item.transaction_id for item in participants if item.dataset_side == DatasetSide.A.value
        )
        target_ids = tuple(
            item.transaction_id for item in participants if item.dataset_side == DatasetSide.B.value
        )
        rule = (
            RuleReference(model.rule_id, cast(str, model.rule_version))
            if model.rule_id is not None
            else None
        )
        return ReconciliationDecision(
            decision_id=model.decision_id,
            status=MatchStatus(model.status),
            source_ids=source_ids,
            target_ids=target_ids,
            rule=rule,
            confidence=model.confidence,
            explanation=MatchExplanation(model.summary, tuple(model.evidence)),
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
        with self._session() as session:
            changed_run_id = session.scalar(
                update(RunModel)
                .where(
                    RunModel.run_id == run_id,
                    RunModel.status.in_(item.value for item in expected),
                )
                .values(status=status.value, updated_at=changed_at, error_code=error_code)
                .returning(RunModel.run_id)
            )
            if changed_run_id is None:
                return None
            model = session.get(RunModel, run_id)
            if model is None:
                raise NotFoundError("a execução não existe")
            return self._bundle(session, model)

    def save_result(self, run_id: str, result: ReconciliationResult) -> RunBundle:
        with self._session() as session:
            run = session.get(RunModel, run_id)
            if run is None:
                raise NotFoundError("a execução não existe")
            if run.status != RunStatus.RUNNING.value:
                raise ConflictError(
                    "os resultados só podem ser salvos durante uma execução em andamento"
                )
            existing = session.scalar(
                select(DecisionModel).where(DecisionModel.run_id == run_id).limit(1)
            )
            if existing is not None:
                current = self._bundle(session, run)
                if current.decisions == result.decisions:
                    return current
                raise ConflictError("as decisões da execução não podem ser alteradas")
            for decision in result.decisions:
                session.add(
                    DecisionModel(
                        run_id=run_id,
                        decision_id=decision.decision_id,
                        status=decision.status.value,
                        rule_id=decision.rule.rule_id if decision.rule else None,
                        rule_version=decision.rule.version if decision.rule else None,
                        confidence=decision.confidence,
                        summary=decision.explanation.summary,
                        evidence=list(decision.explanation.evidence),
                    )
                )
                session.add_all(
                    [
                        MatchParticipantModel(
                            run_id=run_id,
                            decision_id=decision.decision_id,
                            transaction_id=participant,
                            dataset_side=side.value,
                        )
                        for side, participant_ids in (
                            (DatasetSide.A, decision.source_ids),
                            (DatasetSide.B, decision.target_ids),
                        )
                        for participant in participant_ids
                    ]
                )
            session.flush()
            return self._bundle(session, run)

    def add_review(self, event: ManualReviewEvent) -> ManualReviewEvent:
        with self._session() as session:
            existing = session.scalar(
                select(ManualReviewModel).where(
                    ManualReviewModel.idempotency_key == event.idempotency_key
                )
            )
            if existing is not None:
                return self._review(existing)
            session.add(
                ManualReviewModel(
                    event_id=event.event_id,
                    run_id=event.run_id,
                    decision_id=event.decision_id,
                    action=event.action.value,
                    actor_id=event.actor_id,
                    reason=event.reason,
                    idempotency_key=event.idempotency_key,
                    created_at=event.created_at,
                )
            )
        return event

    def find_review_by_idempotency_key(self, key: str) -> ManualReviewEvent | None:
        with self._session() as session:
            model = session.scalar(
                select(ManualReviewModel).where(ManualReviewModel.idempotency_key == key)
            )
            return self._review(model) if model is not None else None

    @staticmethod
    def _review(model: ManualReviewModel) -> ManualReviewEvent:
        return ManualReviewEvent(
            model.event_id,
            model.run_id,
            model.decision_id,
            ManualAction(model.action),
            model.actor_id,
            model.reason,
            model.idempotency_key,
            _aware(model.created_at),
        )

    def list_reviews(self, run_id: str) -> tuple[ManualReviewEvent, ...]:
        with self._session() as session:
            models = session.scalars(
                select(ManualReviewModel)
                .where(ManualReviewModel.run_id == run_id)
                .order_by(ManualReviewModel.created_at, ManualReviewModel.event_id)
            ).all()
            return tuple(self._review(model) for model in models)

    def add_audit(self, event: AuditEvent) -> AuditEvent:
        with self._session() as session:
            existing = session.scalar(
                select(AuditEventModel).where(
                    AuditEventModel.idempotency_key == event.idempotency_key
                )
            )
            if existing is not None:
                return self._audit(existing)
            session.add(
                AuditEventModel(
                    event_id=event.event_id,
                    run_id=event.run_id,
                    event_type=event.event_type,
                    actor_id=event.actor_id,
                    detail=event.detail,
                    idempotency_key=event.idempotency_key,
                    created_at=event.created_at,
                )
            )
        return event

    @staticmethod
    def _audit(model: AuditEventModel) -> AuditEvent:
        return AuditEvent(
            model.event_id,
            model.run_id,
            model.event_type,
            model.actor_id,
            model.detail,
            model.idempotency_key,
            _aware(model.created_at),
        )

    def list_audit(self, run_id: str) -> tuple[AuditEvent, ...]:
        with self._session() as session:
            models = session.scalars(
                select(AuditEventModel)
                .where(AuditEventModel.run_id == run_id)
                .order_by(AuditEventModel.created_at, AuditEventModel.event_id)
            ).all()
            return tuple(self._audit(model) for model in models)

    def add_export(self, artifact: ExportArtifact) -> ExportArtifact:
        with self._session() as session:
            existing = session.scalar(
                select(ExportModel).where(ExportModel.idempotency_key == artifact.idempotency_key)
            )
            if existing is not None:
                return self._export(existing)
            session.add(
                ExportModel(
                    export_id=artifact.export_id,
                    run_id=artifact.run_id,
                    filename=artifact.filename,
                    content_type=artifact.content_type,
                    content=artifact.content,
                    fingerprint=artifact.fingerprint.sha256,
                    idempotency_key=artifact.idempotency_key,
                    created_at=artifact.created_at,
                )
            )
        return artifact

    def find_export_by_idempotency_key(self, key: str) -> ExportArtifact | None:
        with self._session() as session:
            model = session.scalar(select(ExportModel).where(ExportModel.idempotency_key == key))
            return self._export(model) if model is not None else None

    @staticmethod
    def _export(model: ExportModel) -> ExportArtifact:
        return ExportArtifact(
            model.export_id,
            model.run_id,
            model.filename,
            model.content_type,
            model.content,
            DatasetFingerprint(model.fingerprint),
            model.idempotency_key,
            _aware(model.created_at),
        )
