"""Use cases for ingestion, mapping, runs, review, and reporting."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from reconcileflow.application.errors import (
    ConflictError,
    DatasetValidationError,
    NotFoundError,
    PermanentApplicationError,
    ValidationIssue,
)
from reconcileflow.application.models import (
    AuditEvent,
    DatasetRecord,
    ExportArtifact,
    ManualReviewEvent,
    ReportPayload,
    RuleSetSnapshot,
    RunBundle,
)
from reconcileflow.application.ports import (
    Authorizer,
    Clock,
    DatasetParser,
    IdGenerator,
    JobDispatcher,
    ReportBuilder,
    Repository,
)
from reconcileflow.domain.errors import DomainError
from reconcileflow.domain.matching import (
    AmountDateToleranceConfig,
    AmountDateToleranceRule,
    BoundedSplitConfig,
    BoundedSplitRule,
    ExactCompositeConfig,
    ExactCompositeRule,
    ReconciliationEngine,
)
from reconcileflow.domain.models import (
    DatasetFingerprint,
    DatasetSide,
    ManualAction,
    MatchStatus,
    ReconciliationRun,
    RunStatus,
)
from reconcileflow.domain.normalization import (
    NORMALIZATION_VERSION,
    CanonicalMapping,
    normalize_row,
)

_MAX_VALIDATION_ISSUES = 100


class DatasetService:
    def __init__(
        self,
        repository: Repository,
        parser: DatasetParser,
        ids: IdGenerator,
        clock: Clock,
    ) -> None:
        self.repository = repository
        self.parser = parser
        self.ids = ids
        self.clock = clock

    def create(
        self, *, name: str, side: DatasetSide, content_type: str, content: bytes
    ) -> DatasetRecord:
        parsed = self.parser.parse(filename=name, content_type=content_type, content=content)
        dataset = DatasetRecord(
            dataset_id=self.ids.new("dataset"),
            name=name,
            side=side,
            content_type=content_type,
            fingerprint=parsed.fingerprint,
            headers=parsed.headers,
            rows=parsed.rows,
            byte_size=parsed.byte_size,
            created_at=self.clock.now(),
        )
        return self.repository.add_dataset(dataset)

    def map(self, dataset_id: str, mapping: CanonicalMapping) -> DatasetRecord:
        dataset = self.repository.get_dataset(dataset_id)
        if dataset is None:
            raise NotFoundError(f"a fonte de dados {dataset_id!r} não foi encontrada")
        mapped_columns = (
            mapping.amount,
            mapping.booking_date,
            mapping.currency,
            mapping.transaction_id,
            mapping.source_record_id,
            mapping.document,
            mapping.reference,
        )
        missing_columns = sorted(
            {
                column
                for column in mapped_columns
                if column is not None and column not in dataset.headers
            }
        )
        if missing_columns:
            raise DatasetValidationError(
                tuple(
                    ValidationIssue(
                        code="missing_mapped_column",
                        message=f"a coluna mapeada não foi encontrada: {column}",
                        field=column,
                    )
                    for column in missing_columns
                )
            )
        transactions = []
        transaction_rows: dict[str, int] = {}
        issues: list[ValidationIssue] = []
        for row_index, row in enumerate(dataset.rows, start=2):
            try:
                transaction = normalize_row(
                    row,
                    mapping=mapping,
                    dataset_id=dataset.dataset_id,
                    side=dataset.side,
                    fingerprint=dataset.fingerprint,
                    row_number=row_index,
                )
                first_row = transaction_rows.get(transaction.transaction_id)
                if first_row is not None:
                    issues.append(
                        ValidationIssue(
                            code="duplicate_transaction_id",
                            message=f"o identificador da transação repete o da linha {first_row}",
                            row=row_index,
                            field=mapping.transaction_id,
                        )
                    )
                else:
                    transaction_rows[transaction.transaction_id] = row_index
                    transactions.append(transaction)
            except DomainError as error:
                issues.append(
                    ValidationIssue(code="normalization_error", message=str(error), row=row_index)
                )
            if len(issues) >= _MAX_VALIDATION_ISSUES:
                issues.append(
                    ValidationIssue(
                        code="validation_issue_limit",
                        message=(
                            "a validação foi interrompida após "
                            f"{_MAX_VALIDATION_ISSUES} ocorrências"
                        ),
                    )
                )
                break
        if issues:
            raise DatasetValidationError(tuple(issues))
        if not transactions:
            raise DatasetValidationError(
                (ValidationIssue("empty_dataset", "a fonte de dados não contém registros"),)
            )
        updated = replace(dataset, mapping=mapping, transactions=tuple(transactions))
        return self.repository.save_mapping(updated)


def build_engine(profile: RuleSetSnapshot) -> ReconciliationEngine:
    amount_tolerance = Decimal(profile.amount_tolerance)
    rules: list[object] = [ExactCompositeRule(ExactCompositeConfig(profile.exact_fields))]
    rules.append(
        AmountDateToleranceRule(
            AmountDateToleranceConfig(amount_tolerance, profile.date_tolerance_days)
        )
    )
    if profile.split_enabled:
        rules.append(
            BoundedSplitRule(
                BoundedSplitConfig(
                    amount_tolerance=amount_tolerance,
                    date_tolerance_days=profile.date_tolerance_days,
                    max_group_size=profile.max_group_size,
                    max_candidate_pool=profile.max_candidate_pool,
                    max_combinations=profile.max_combinations,
                )
            )
        )
    return ReconciliationEngine(tuple(rules))  # type: ignore[arg-type]


class RunService:
    def __init__(
        self,
        repository: Repository,
        dispatcher: JobDispatcher,
        ids: IdGenerator,
        clock: Clock,
        *,
        async_row_threshold: int,
    ) -> None:
        self.repository = repository
        self.dispatcher = dispatcher
        self.ids = ids
        self.clock = clock
        self.async_row_threshold = async_row_threshold

    def start(
        self,
        *,
        dataset_a_id: str,
        dataset_b_id: str,
        profile: RuleSetSnapshot,
        idempotency_key: str,
        correlation_id: str,
    ) -> RunBundle:
        existing = self.repository.find_run_by_idempotency_key(idempotency_key)
        if existing is not None:
            same_request = (
                existing.dataset_a_id == dataset_a_id
                and existing.dataset_b_id == dataset_b_id
                and existing.profile.reference == profile.reference
            )
            if not same_request:
                raise ConflictError("a chave de idempotência já foi usada em outra execução")
            if existing.run.status is RunStatus.QUEUED:
                self.dispatcher.dispatch_reconciliation(existing.run.run_id)
            return existing
        dataset_a = self._mapped_dataset(dataset_a_id, DatasetSide.A)
        dataset_b = self._mapped_dataset(dataset_b_id, DatasetSide.B)
        self.repository.add_rule_set(profile)
        now = self.clock.now()
        run = ReconciliationRun(
            run_id=self.ids.new("run"),
            dataset_a=dataset_a.fingerprint,
            dataset_b=dataset_b.fingerprint,
            rule_set=profile.reference,
            normalization_version=NORMALIZATION_VERSION,
            status=RunStatus.PENDING,
            created_at=now,
            updated_at=now,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )
        self.repository.add_run(RunBundle(run, dataset_a.dataset_id, dataset_b.dataset_id, profile))
        row_count = len(dataset_a.transactions) + len(dataset_b.transactions)
        if row_count >= self.async_row_threshold:
            queued = self.repository.transition_run(
                run.run_id, frozenset({RunStatus.PENDING}), RunStatus.QUEUED, self.clock.now()
            )
            if queued is None:
                raise ConflictError("não foi possível colocar a execução na fila")
            self.dispatcher.dispatch_reconciliation(run.run_id)
            return queued
        return self.execute(run.run_id)

    def execute(self, run_id: str, *, recover_running: bool = False) -> RunBundle:
        bundle = self.repository.get_run(run_id)
        if bundle is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        if bundle.run.status is RunStatus.COMPLETED:
            return bundle
        if recover_running and bundle.run.status is RunStatus.RUNNING:
            recovered = self.repository.transition_run(
                run_id,
                frozenset({RunStatus.RUNNING}),
                RunStatus.QUEUED,
                self.clock.now(),
            )
            if recovered is None:
                current = self.repository.get_run(run_id)
                if current is not None and current.run.status is RunStatus.COMPLETED:
                    return current
                raise ConflictError("a nova tentativa não conseguiu recuperar a execução")
        claimed = self.repository.transition_run(
            run_id,
            frozenset({RunStatus.PENDING, RunStatus.QUEUED}),
            RunStatus.RUNNING,
            self.clock.now(),
        )
        if claimed is None:
            current = self.repository.get_run(run_id)
            if current is not None and current.run.status is RunStatus.COMPLETED:
                return current
            raise ConflictError("a execução já está em andamento ou foi encerrada")
        try:
            dataset_a = self._mapped_dataset(claimed.dataset_a_id, DatasetSide.A)
            dataset_b = self._mapped_dataset(claimed.dataset_b_id, DatasetSide.B)
            result = build_engine(claimed.profile).reconcile(
                run_id=run_id,
                transactions=(*dataset_a.transactions, *dataset_b.transactions),
            )
            self.repository.save_result(run_id, result)
            completed = self.repository.transition_run(
                run_id,
                frozenset({RunStatus.RUNNING}),
                RunStatus.COMPLETED,
                self.clock.now(),
            )
            if completed is None:
                raise ConflictError("o resultado foi salvo, mas a conclusão da execução falhou")
            return completed
        except (DomainError, DatasetValidationError, PermanentApplicationError):
            self.repository.transition_run(
                run_id,
                frozenset({RunStatus.RUNNING}),
                RunStatus.FAILED,
                self.clock.now(),
                error_code="permanent_processing_error",
            )
            raise

    def _mapped_dataset(self, dataset_id: str, expected_side: DatasetSide) -> DatasetRecord:
        dataset = self.repository.get_dataset(dataset_id)
        if dataset is None:
            raise NotFoundError(f"a fonte de dados {dataset_id!r} não foi encontrada")
        if dataset.side is not expected_side:
            raise ConflictError(
                f"a fonte de dados {dataset_id!r} deve pertencer ao lado {expected_side}"
            )
        if not dataset.is_mapped:
            raise ConflictError(f"a fonte de dados {dataset_id!r} ainda não foi mapeada")
        return dataset


class ReviewService:
    def __init__(
        self,
        repository: Repository,
        authorizer: Authorizer,
        ids: IdGenerator,
        clock: Clock,
    ) -> None:
        self.repository = repository
        self.authorizer = authorizer
        self.ids = ids
        self.clock = clock

    def record(
        self,
        *,
        run_id: str,
        decision_id: str,
        action: ManualAction,
        actor_id: str,
        reason: str,
        idempotency_key: str,
    ) -> ManualReviewEvent:
        self.authorizer.require(actor_id, "review:write")
        existing = self.repository.find_review_by_idempotency_key(idempotency_key)
        if existing is not None:
            same_request = (
                existing.run_id == run_id
                and existing.decision_id == decision_id
                and existing.action is action
                and existing.actor_id == actor_id
                and existing.reason == reason.strip()
            )
            if not same_request:
                raise ConflictError("a chave de idempotência já foi usada em outra revisão")
            self._record_audit(existing)
            return existing
        bundle = self.repository.get_run(run_id)
        if bundle is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        decision = next(
            (item for item in bundle.decisions if item.decision_id == decision_id), None
        )
        if decision is None:
            raise NotFoundError(f"a decisão {decision_id!r} não foi encontrada")
        if decision.status not in {MatchStatus.AMBIGUOUS, MatchStatus.MANUAL_REVIEW}:
            raise ConflictError(
                "somente decisões ambíguas ou encaminhadas manualmente podem ser revisadas"
            )
        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise ConflictError("informe o motivo da decisão manual")
        event = ManualReviewEvent(
            event_id=self.ids.new("review"),
            run_id=run_id,
            decision_id=decision_id,
            action=action,
            actor_id=actor_id,
            reason=cleaned_reason,
            idempotency_key=idempotency_key,
            created_at=self.clock.now(),
        )
        stored = self.repository.add_review(event)
        self._record_audit(stored)
        return stored

    def _record_audit(self, event: ManualReviewEvent) -> None:
        self.repository.add_audit(
            AuditEvent(
                event_id=self.ids.new("audit"),
                run_id=event.run_id,
                event_type="manual_review_recorded",
                actor_id=event.actor_id,
                detail=(
                    f"Aprovação registrada para a decisão {event.decision_id}."
                    if event.action is ManualAction.APPROVE
                    else f"Rejeição registrada para a decisão {event.decision_id}."
                ),
                idempotency_key=f"audit:{event.idempotency_key}",
                created_at=event.created_at,
            )
        )


class ExportService:
    def __init__(
        self,
        repository: Repository,
        report_builder: ReportBuilder,
        authorizer: Authorizer,
        ids: IdGenerator,
        clock: Clock,
    ) -> None:
        self.repository = repository
        self.report_builder = report_builder
        self.authorizer = authorizer
        self.ids = ids
        self.clock = clock

    def create(self, *, run_id: str, actor_id: str, idempotency_key: str) -> ExportArtifact:
        self.authorizer.require(actor_id, "export:write")
        existing = self.repository.find_export_by_idempotency_key(idempotency_key)
        if existing is not None:
            if existing.run_id != run_id:
                raise ConflictError("a chave de idempotência já foi usada em outra exportação")
            self._record_audit(existing, actor_id)
            return existing
        bundle = self.repository.get_run(run_id)
        if bundle is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        if bundle.run.status is not RunStatus.COMPLETED:
            raise ConflictError("somente conciliações concluídas podem ser exportadas")
        dataset_a = self.repository.get_dataset(bundle.dataset_a_id)
        dataset_b = self.repository.get_dataset(bundle.dataset_b_id)
        if dataset_a is None or dataset_b is None:
            raise NotFoundError("as fontes de dados desta conciliação não estão disponíveis")
        content = self.report_builder.build(
            ReportPayload(
                run=bundle.run,
                decisions=bundle.decisions,
                transactions=(*dataset_a.transactions, *dataset_b.transactions),
                reviews=self.repository.list_reviews(run_id),
            )
        )
        artifact = ExportArtifact(
            export_id=self.ids.new("export"),
            run_id=run_id,
            filename=f"reconcileflow-{run_id}.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content,
            fingerprint=DatasetFingerprint.from_bytes(content),
            idempotency_key=idempotency_key,
            created_at=self.clock.now(),
        )
        stored = self.repository.add_export(artifact)
        self._record_audit(stored, actor_id)
        return stored

    def _record_audit(self, artifact: ExportArtifact, actor_id: str) -> None:
        self.repository.add_audit(
            AuditEvent(
                event_id=self.ids.new("audit"),
                run_id=artifact.run_id,
                event_type="report_exported",
                actor_id=actor_id,
                detail=artifact.fingerprint.short(),
                idempotency_key=f"audit:{artifact.idempotency_key}",
                created_at=artifact.created_at,
            )
        )
