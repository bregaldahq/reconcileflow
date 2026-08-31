"""FastAPI transport and composition-safe route orchestration."""

from __future__ import annotations

import time
import uuid
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

import structlog
from fastapi import FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from opentelemetry import trace

from reconcileflow.api.schemas import (
    AuditResponse,
    DatasetResponse,
    DecisionResponse,
    MappingRequest,
    ProfileResponse,
    ReviewRequest,
    ReviewResponse,
    RunResponse,
    StartRunRequest,
)
from reconcileflow.application.errors import (
    ApplicationError,
    AuthorizationError,
    ConflictError,
    DatasetValidationError,
    NotFoundError,
)
from reconcileflow.application.models import DatasetRecord, RunBundle
from reconcileflow.bootstrap import Container, get_container
from reconcileflow.domain.errors import DomainError
from reconcileflow.domain.models import DatasetSide, MatchStatus, ReconciliationDecision, RunStatus
from reconcileflow.domain.normalization import CanonicalMapping
from reconcileflow.observability import (
    configure_observability,
    correlation_id_context,
    log_run_outcome,
)

_CORRELATION_ID_MAX_LENGTH = 100
_VALIDATION_MESSAGES = {
    "missing": "Campo obrigatório.",
    "string_type": "Informe um texto válido.",
    "string_too_short": "O texto é menor que o mínimo permitido.",
    "string_too_long": "O texto ultrapassa o tamanho máximo permitido.",
    "literal_error": "O valor informado não é uma opção aceita.",
    "enum": "Selecione uma opção válida.",
    "decimal_parsing": "Informe um número decimal válido.",
    "int_parsing": "Informe um número inteiro válido.",
    "greater_than_equal": "O valor é menor que o mínimo permitido.",
    "less_than_equal": "O valor ultrapassa o máximo permitido.",
}


def _localized_validation_message(error: dict[str, object]) -> str:
    error_type = str(error.get("type", ""))
    if error_type == "value_error":
        original = str(error.get("msg", ""))
        _, separator, detail = original.partition(", ")
        if separator and detail:
            return detail[:1].upper() + detail[1:] + ("" if detail.endswith(".") else ".")
    return _VALIDATION_MESSAGES.get(error_type, "O valor informado não é válido.")


def _dataset_response(dataset: DatasetRecord) -> DatasetResponse:
    return DatasetResponse(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        side=dataset.side.value,
        fingerprint=dataset.fingerprint.sha256,
        headers=list(dataset.headers),
        row_count=len(dataset.rows),
        byte_size=dataset.byte_size,
        is_mapped=dataset.is_mapped,
        created_at=dataset.created_at,
    )


def _run_response(bundle: RunBundle) -> RunResponse:
    counts = Counter(item.status.value for item in bundle.decisions)
    progress = {
        RunStatus.PENDING: 0,
        RunStatus.QUEUED: 10,
        RunStatus.RUNNING: 50,
        RunStatus.COMPLETED: 100,
        RunStatus.FAILED: 100,
    }[bundle.run.status]
    return RunResponse(
        run_id=bundle.run.run_id,
        dataset_a_id=bundle.dataset_a_id,
        dataset_b_id=bundle.dataset_b_id,
        dataset_a_fingerprint=bundle.run.dataset_a.sha256,
        dataset_b_fingerprint=bundle.run.dataset_b.sha256,
        rule_id=bundle.run.rule_set.rule_id,
        rule_version=bundle.run.rule_set.version,
        normalization_version=bundle.run.normalization_version,
        status=bundle.run.status,
        progress_percent=progress,
        counts={status.value: counts[status.value] for status in MatchStatus},
        created_at=bundle.run.created_at,
        updated_at=bundle.run.updated_at,
        correlation_id=bundle.run.correlation_id,
        error_code=bundle.error_code,
    )


def _decision_response(decision: ReconciliationDecision) -> DecisionResponse:
    return DecisionResponse(
        decision_id=decision.decision_id,
        status=decision.status,
        source_ids=list(decision.source_ids),
        target_ids=list(decision.target_ids),
        rule_id=decision.rule.rule_id if decision.rule else None,
        rule_version=decision.rule.version if decision.rule else None,
        confidence=decision.confidence,
        explanation=decision.explanation.summary,
        evidence=list(decision.explanation.evidence),
    )


def create_app(container: Container | None = None) -> FastAPI:  # noqa: PLR0915
    services = container or get_container()
    configure_observability(
        log_level=services.settings.log_level,
        otel_enabled=services.settings.otel_enabled,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        del application
        yield

    app = FastAPI(
        title="ReconcileFlow API",
        version="1.0.0",
        description="Conciliação de transações determinística, explicável e auditável.",
        lifespan=lifespan,
    )
    app.state.container = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(services.settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "X-Actor-Id", "X-Correlation-Id", "X-Idempotency-Key"],
    )

    @app.middleware("http")
    async def correlation_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied_correlation_id = request.headers.get("X-Correlation-Id")
        correlation_id = supplied_correlation_id or str(uuid.uuid4())
        if len(correlation_id) > _CORRELATION_ID_MAX_LENGTH:
            fallback_id = str(uuid.uuid4())
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "invalid_correlation_id",
                        "message": "X-Correlation-Id não pode ultrapassar 100 caracteres",
                    },
                    "correlation_id": fallback_id,
                },
                headers={"X-Correlation-Id": fallback_id},
            )
        token = correlation_id_context.set(correlation_id)
        started = time.perf_counter()
        tracer = trace.get_tracer("reconcileflow.api")
        try:
            with tracer.start_as_current_span(f"{request.method} {request.url.path}"):
                response = await call_next(request)
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            structlog.get_logger("reconcileflow.http").info(
                "http_request",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            correlation_id_context.reset(token)
        response.headers["X-Correlation-Id"] = correlation_id
        return response

    def error_response(code: str, message: str, status: int, issues: object = None) -> JSONResponse:
        detail: dict[str, object] = {"code": code, "message": message}
        if issues is not None:
            detail["issues"] = issues
        return JSONResponse(
            status_code=status,
            content={"error": detail, "correlation_id": correlation_id_context.get()},
        )

    @app.exception_handler(DatasetValidationError)
    async def dataset_validation_handler(
        request: Request, error: DatasetValidationError
    ) -> JSONResponse:
        del request
        issues = [
            {"code": item.code, "message": item.message, "row": item.row, "field": item.field}
            for item in error.issues
        ]
        return error_response("dataset_validation_failed", str(error), 422, issues)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del request
        issues = jsonable_encoder(error.errors())
        for issue in issues:
            issue["msg"] = _localized_validation_message(issue)
        return error_response(
            "request_validation_failed",
            "A solicitação contém dados inválidos.",
            422,
            issues,
        )

    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, error: ApplicationError) -> JSONResponse:
        del request
        if isinstance(error, NotFoundError):
            return error_response("not_found", str(error), 404)
        if isinstance(error, ConflictError):
            return error_response("conflict", str(error), 409)
        if isinstance(error, AuthorizationError):
            return error_response("forbidden", str(error), 403)
        return error_response("application_error", str(error), 400)

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, error: DomainError) -> JSONResponse:
        del request
        return error_response("domain_validation_failed", str(error), 422)

    @app.get("/health/live", tags=["health"])
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def readiness() -> dict[str, str]:
        services.repository.list_runs()
        return {"status": "ready"}

    @app.get("/api/v1/profiles", response_model=list[ProfileResponse], tags=["profiles"])
    async def list_profiles() -> list[ProfileResponse]:
        return [
            ProfileResponse(
                rule_id=item.reference.rule_id,
                version=item.reference.version,
                label="Conciliação explicável padrão",
                amount_tolerance=item.amount_tolerance,
                date_tolerance_days=item.date_tolerance_days,
                split_enabled=item.split_enabled,
            )
            for item in services.profiles
        ]

    @app.post(
        "/api/v1/datasets", response_model=DatasetResponse, status_code=201, tags=["datasets"]
    )
    async def create_dataset(
        side: Annotated[DatasetSide, Form()], file: Annotated[UploadFile, File()]
    ) -> DatasetResponse:
        content = await file.read(services.settings.max_upload_bytes + 1)
        dataset = services.datasets.create(
            name=file.filename or "upload",
            side=side,
            content_type=file.content_type or "application/octet-stream",
            content=content,
        )
        return _dataset_response(dataset)

    @app.get("/api/v1/datasets", response_model=list[DatasetResponse], tags=["datasets"])
    async def list_datasets() -> list[DatasetResponse]:
        return [_dataset_response(item) for item in services.repository.list_datasets()]

    @app.get("/api/v1/datasets/{dataset_id}", response_model=DatasetResponse, tags=["datasets"])
    async def get_dataset(dataset_id: str) -> DatasetResponse:
        dataset = services.repository.get_dataset(dataset_id)
        if dataset is None:
            raise NotFoundError(f"a fonte de dados {dataset_id!r} não foi encontrada")
        return _dataset_response(dataset)

    @app.put(
        "/api/v1/datasets/{dataset_id}/mapping",
        response_model=DatasetResponse,
        tags=["datasets"],
    )
    async def map_dataset(dataset_id: str, body: MappingRequest) -> DatasetResponse:
        mapped = services.datasets.map(dataset_id, CanonicalMapping(**body.model_dump()))
        return _dataset_response(mapped)

    @app.post("/api/v1/runs", response_model=RunResponse, status_code=201, tags=["runs"])
    async def start_run(
        body: StartRunRequest,
        request: Request,
        idempotency_key: str = Header(alias="X-Idempotency-Key", min_length=1, max_length=180),
    ) -> RunResponse:
        selected = next(
            (
                item
                for item in services.profiles
                if item.reference.rule_id == body.profile_id
                and item.reference.version == body.profile_version
            ),
            None,
        )
        if selected is None:
            raise NotFoundError("o perfil de conciliação não foi encontrado")
        started = time.perf_counter()
        bundle = services.runs.start(
            dataset_a_id=body.dataset_a_id,
            dataset_b_id=body.dataset_b_id,
            profile=selected,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id_context.get(),
        )
        if bundle.run.status is RunStatus.COMPLETED:
            log_run_outcome(bundle, duration_ms=int((time.perf_counter() - started) * 1000))
        return _run_response(bundle)

    @app.get("/api/v1/runs", response_model=list[RunResponse], tags=["runs"])
    async def list_runs() -> list[RunResponse]:
        return [_run_response(item) for item in services.repository.list_runs()]

    @app.get("/api/v1/runs/{run_id}", response_model=RunResponse, tags=["runs"])
    async def get_run(run_id: str) -> RunResponse:
        bundle = services.repository.get_run(run_id)
        if bundle is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        return _run_response(bundle)

    @app.get(
        "/api/v1/runs/{run_id}/decisions",
        response_model=list[DecisionResponse],
        tags=["runs"],
    )
    async def list_decisions(
        run_id: str, status: Annotated[MatchStatus | None, Query()] = None
    ) -> list[DecisionResponse]:
        bundle = services.repository.get_run(run_id)
        if bundle is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        return [
            _decision_response(item)
            for item in bundle.decisions
            if status is None or item.status is status
        ]

    @app.get(
        "/api/v1/runs/{run_id}/decisions/{decision_id}",
        response_model=DecisionResponse,
        tags=["runs"],
    )
    async def get_decision(run_id: str, decision_id: str) -> DecisionResponse:
        bundle = services.repository.get_run(run_id)
        if bundle is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        decision = next(
            (item for item in bundle.decisions if item.decision_id == decision_id), None
        )
        if decision is None:
            raise NotFoundError(f"a decisão {decision_id!r} não foi encontrada")
        return _decision_response(decision)

    @app.post(
        "/api/v1/runs/{run_id}/decisions/{decision_id}/reviews",
        response_model=ReviewResponse,
        status_code=201,
        tags=["reviews"],
    )
    async def review_decision(
        run_id: str,
        decision_id: str,
        body: ReviewRequest,
        actor_id: str = Header(alias="X-Actor-Id", min_length=1, max_length=255),
        idempotency_key: str = Header(alias="X-Idempotency-Key", min_length=1, max_length=180),
    ) -> ReviewResponse:
        event = services.reviews.record(
            run_id=run_id,
            decision_id=decision_id,
            action=body.action,
            actor_id=actor_id,
            reason=body.reason,
            idempotency_key=idempotency_key,
        )
        return ReviewResponse(
            event_id=event.event_id,
            run_id=event.run_id,
            decision_id=event.decision_id,
            action=event.action,
            actor_id=event.actor_id,
            reason=event.reason,
            created_at=event.created_at,
        )

    @app.get(
        "/api/v1/runs/{run_id}/reviews",
        response_model=list[ReviewResponse],
        tags=["reviews"],
    )
    async def list_reviews(run_id: str) -> list[ReviewResponse]:
        if services.repository.get_run(run_id) is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        return [
            ReviewResponse(
                event_id=item.event_id,
                run_id=item.run_id,
                decision_id=item.decision_id,
                action=item.action,
                actor_id=item.actor_id,
                reason=item.reason,
                created_at=item.created_at,
            )
            for item in services.repository.list_reviews(run_id)
        ]

    @app.get(
        "/api/v1/runs/{run_id}/audit",
        response_model=list[AuditResponse],
        tags=["audit"],
    )
    async def list_audit(run_id: str) -> list[AuditResponse]:
        if services.repository.get_run(run_id) is None:
            raise NotFoundError(f"a execução {run_id!r} não foi encontrada")
        return [
            AuditResponse(
                event_id=item.event_id,
                event_type=item.event_type,
                actor_id=item.actor_id,
                detail=item.detail,
                created_at=item.created_at,
            )
            for item in services.repository.list_audit(run_id)
        ]

    @app.post("/api/v1/runs/{run_id}/exports", tags=["exports"])
    async def create_export(
        run_id: str,
        actor_id: str = Header(alias="X-Actor-Id", min_length=1, max_length=255),
        idempotency_key: str = Header(alias="X-Idempotency-Key", min_length=1, max_length=180),
    ) -> Response:
        artifact = services.exports.create(
            run_id=run_id, actor_id=actor_id, idempotency_key=idempotency_key
        )
        return Response(
            content=artifact.content,
            media_type=artifact.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{artifact.filename}"',
                "ETag": artifact.fingerprint.sha256,
            },
        )

    return app


app = create_app()
