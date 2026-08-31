"""Versioned HTTP request and response contracts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from reconcileflow.domain.models import ManualAction, MatchStatus, RunStatus


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DatasetResponse(StrictModel):
    dataset_id: str
    name: str
    side: str
    fingerprint: str
    headers: list[str]
    row_count: int
    byte_size: int
    is_mapped: bool
    created_at: datetime


class MappingRequest(StrictModel):
    amount: str = Field(min_length=1, max_length=255)
    booking_date: str = Field(min_length=1, max_length=255)
    currency: str | None = Field(default=None, max_length=255)
    transaction_id: str | None = Field(default=None, max_length=255)
    source_record_id: str | None = Field(default=None, max_length=255)
    document: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=255)
    default_currency: str = Field(default="BRL", min_length=3, max_length=3)


class ProfileResponse(StrictModel):
    rule_id: str
    version: str
    label: str
    amount_tolerance: str
    date_tolerance_days: int
    split_enabled: bool


class StartRunRequest(StrictModel):
    dataset_a_id: str = Field(min_length=1, max_length=80)
    dataset_b_id: str = Field(min_length=1, max_length=80)
    profile_id: str = Field(default="standard", min_length=1, max_length=80)
    profile_version: str = Field(default="1", min_length=1, max_length=40)


class DecisionResponse(StrictModel):
    decision_id: str
    status: MatchStatus
    source_ids: list[str]
    target_ids: list[str]
    rule_id: str | None
    rule_version: str | None
    confidence: Decimal | None
    explanation: str
    evidence: list[str]


class RunResponse(StrictModel):
    run_id: str
    dataset_a_id: str
    dataset_b_id: str
    dataset_a_fingerprint: str
    dataset_b_fingerprint: str
    rule_id: str
    rule_version: str
    normalization_version: str
    status: RunStatus
    progress_percent: int
    counts: dict[str, int]
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    error_code: str | None


class ReviewRequest(StrictModel):
    action: ManualAction
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("o motivo não pode conter apenas espaços")
        return value.strip()


class ReviewResponse(StrictModel):
    event_id: str
    run_id: str
    decision_id: str
    action: ManualAction
    actor_id: str
    reason: str
    created_at: datetime


class AuditResponse(StrictModel):
    event_id: str
    event_type: str
    actor_id: str
    detail: str
    created_at: datetime


class CanonicalTransactionResponse(StrictModel):
    transaction_id: str
    side: str
    amount: Decimal
    currency: str
    booking_date: date
    document: str | None
    reference: str | None
