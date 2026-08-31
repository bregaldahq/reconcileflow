from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from reconcileflow.domain.errors import DomainError, InvalidTransitionError, MonetaryFloatError
from reconcileflow.domain.models import (
    CanonicalTransaction,
    DatasetFingerprint,
    DatasetSide,
    MatchExplanation,
    MatchStatus,
    Money,
    ReconciliationDecision,
    ReconciliationResult,
    ReconciliationRun,
    RuleReference,
    RunStatus,
)


def test_money_rejects_binary_float() -> None:
    with pytest.raises(MonetaryFloatError):
        Money(12.3, "BRL")  # type: ignore[arg-type]


def test_money_normalizes_currency_and_is_immutable() -> None:
    money = Money(Decimal("12.30"), " brl ")
    assert money.currency == "BRL"
    with pytest.raises(FrozenInstanceError):
        money.currency = "USD"  # type: ignore[misc]


@pytest.mark.parametrize("currency", ["", "BR", "REAL", "12R"])
def test_money_rejects_invalid_currency(currency: str) -> None:
    with pytest.raises(DomainError):
        Money(Decimal("1"), currency)


def test_dataset_fingerprint_is_deterministic() -> None:
    first = DatasetFingerprint.from_bytes(b"same")
    second = DatasetFingerprint.from_bytes(b"same")
    assert first == second
    assert first.short() == first.sha256[:12]
    with pytest.raises(DomainError):
        DatasetFingerprint("not-a-digest")


def test_explanation_evidence_is_unique_and_sorted() -> None:
    explanation = MatchExplanation("Equal fields", ("z", "a", "z"))
    assert explanation.evidence == ("a", "z")


def test_transaction_rejects_datetime_for_booking_date() -> None:
    with pytest.raises(DomainError):
        CanonicalTransaction(
            transaction_id="a:1",
            dataset_id="a",
            side=DatasetSide.A,
            money=Money(Decimal("1"), "BRL"),
            booking_date=datetime.now(UTC),  # type: ignore[arg-type]
            source_record_id="1",
        )


def test_result_rejects_participant_reuse() -> None:
    explanation = MatchExplanation("No match", ("pipeline exhausted",))
    decision_a = ReconciliationDecision("d1", MatchStatus.UNMATCHED, ("a:1",), (), explanation)
    decision_b = ReconciliationDecision("d2", MatchStatus.MANUAL_REVIEW, ("a:1",), (), explanation)
    with pytest.raises(DomainError, match="mais de uma decisão"):
        ReconciliationResult("run-1", (decision_a, decision_b))


def test_completed_run_is_immutable_and_transitions_are_guarded() -> None:
    now = datetime.now(UTC)
    run = ReconciliationRun(
        run_id="run-1",
        dataset_a=DatasetFingerprint.from_bytes(b"a"),
        dataset_b=DatasetFingerprint.from_bytes(b"b"),
        rule_set=RuleReference("standard", "1"),
        normalization_version="br-v1",
        status=RunStatus.PENDING,
        created_at=now,
        updated_at=now,
        correlation_id="correlation-1",
        idempotency_key="idem-1",
    )
    running = run.transition(RunStatus.RUNNING, at=now + timedelta(seconds=1))
    completed = running.transition(RunStatus.COMPLETED, at=now + timedelta(seconds=2))
    assert run.status is RunStatus.PENDING
    assert completed.status is RunStatus.COMPLETED
    with pytest.raises(InvalidTransitionError):
        completed.transition(RunStatus.RUNNING)


def test_automatic_decision_requires_rule_and_confidence() -> None:
    with pytest.raises(DomainError, match="decisões automáticas"):
        ReconciliationDecision(
            "decision",
            MatchStatus.MATCHED,
            ("a:1",),
            ("b:1",),
            MatchExplanation("Match", ("equal",)),
        )


def test_transaction_exposes_only_supported_match_fields(transaction_factory) -> None:
    transaction = transaction_factory("1", DatasetSide.A, "10")
    assert transaction.field_value("amount") == Decimal("10")
    assert transaction.booking_date == date(2026, 1, 15)
    with pytest.raises(DomainError, match="não aceito"):
        transaction.field_value("unknown")
