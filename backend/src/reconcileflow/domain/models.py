"""Immutable canonical objects used by the reconciliation engine."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from reconcileflow.domain.errors import (
    DomainError,
    InvalidTransitionError,
    MonetaryFloatError,
)

_CURRENCY_CODE_LENGTH = 3
_SHA256_HEX_LENGTH = 64
_FIELD_LABELS = {
    "amount": "o valor",
    "currency": "a moeda",
    "rule_id": "o identificador da regra",
    "rule version": "a versão da regra",
    "explanation summary": "o resumo da explicação",
    "evidence item": "o item de evidência",
    "transaction_id": "o identificador da transação",
    "dataset_id": "o identificador da fonte de dados",
    "source_record_id": "o identificador do registro original",
    "document": "o documento",
    "reference": "a referência",
    "source participant": "o participante da origem",
    "target participant": "o participante do destino",
    "confidence": "a confiança",
    "decision_id": "o identificador da decisão",
    "run_id": "o identificador da execução",
    "normalization_version": "a versão da normalização",
    "correlation_id": "o identificador de correlação",
    "idempotency_key": "a chave de idempotência",
    "created_at": "a data de criação",
    "updated_at": "a data de atualização",
}


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainError(f"{_FIELD_LABELS.get(field_name, field_name)} não pode ficar vazio")
    return normalized


def _decimal(value: object, field_name: str) -> Decimal:
    label = _FIELD_LABELS.get(field_name, field_name)
    if isinstance(value, float):
        raise MonetaryFloatError(f"{label} não pode ser um número binário de ponto flutuante")
    if not isinstance(value, Decimal):
        raise DomainError(f"{label} deve ser do tipo Decimal")
    if not value.is_finite():
        raise DomainError(f"{label} deve ser finito")
    return value


class DatasetSide(StrEnum):
    A = "A"
    B = "B"


class MatchStatus(StrEnum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    DUPLICATE = "DUPLICATE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    SPLIT_MATCHED = "SPLIT_MATCHED"


class RunStatus(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ManualAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _decimal(self.amount, "amount"))
        currency = _required_text(self.currency, "currency").upper()
        if len(currency) != _CURRENCY_CODE_LENGTH or not currency.isalpha():
            raise DomainError("a moeda deve ser um código alfabético de três letras")
        object.__setattr__(self, "currency", currency)


@dataclass(frozen=True, slots=True)
class DatasetFingerprint:
    sha256: str

    def __post_init__(self) -> None:
        digest = self.sha256.lower()
        if len(digest) != _SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise DomainError(
                "a impressão digital da fonte deve ser um código SHA-256 "
                "hexadecimal de 64 caracteres"
            )
        object.__setattr__(self, "sha256", digest)

    @classmethod
    def from_bytes(cls, content: bytes) -> DatasetFingerprint:
        return cls(hashlib.sha256(content).hexdigest())

    def short(self) -> str:
        return self.sha256[:12]


@dataclass(frozen=True, slots=True)
class RuleReference:
    rule_id: str
    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_id", _required_text(self.rule_id, "rule_id"))
        object.__setattr__(self, "version", _required_text(self.version, "rule version"))


@dataclass(frozen=True, slots=True)
class MatchExplanation:
    summary: str
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", _required_text(self.summary, "explanation summary"))
        cleaned = tuple(sorted({_required_text(item, "evidence item") for item in self.evidence}))
        if not cleaned:
            raise DomainError("a explicação da conciliação exige evidências")
        object.__setattr__(self, "evidence", cleaned)


@dataclass(frozen=True, slots=True)
class CanonicalTransaction:
    transaction_id: str
    dataset_id: str
    side: DatasetSide
    money: Money
    booking_date: date
    source_record_id: str
    document: str | None = None
    reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "transaction_id", _required_text(self.transaction_id, "transaction_id")
        )
        object.__setattr__(self, "dataset_id", _required_text(self.dataset_id, "dataset_id"))
        object.__setattr__(
            self,
            "source_record_id",
            _required_text(self.source_record_id, "source_record_id"),
        )
        if not isinstance(self.booking_date, date) or isinstance(self.booking_date, datetime):
            raise DomainError("a data de lançamento deve ser uma data válida")
        if self.document is not None:
            object.__setattr__(self, "document", _required_text(self.document, "document"))
        if self.reference is not None:
            object.__setattr__(self, "reference", _required_text(self.reference, "reference"))

    def field_value(self, name: str) -> str | Decimal | date | None:
        values: dict[str, str | Decimal | date | None] = {
            "amount": self.money.amount,
            "currency": self.money.currency,
            "date": self.booking_date,
            "document": self.document,
            "reference": self.reference,
            "source_record_id": self.source_record_id,
        }
        if name not in values:
            raise DomainError(f"campo canônico de conciliação não aceito: {name}")
        return values[name]

    def duplicate_key(self) -> tuple[object, ...]:
        return (
            self.money.currency,
            self.money.amount,
            self.booking_date.isoformat(),
            self.document,
            self.reference,
        )


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    source_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    rule: RuleReference
    confidence: Decimal
    explanation: MatchExplanation
    status: MatchStatus = MatchStatus.MATCHED

    def __post_init__(self) -> None:
        sources = tuple(
            sorted({_required_text(item, "source participant") for item in self.source_ids})
        )
        targets = tuple(
            sorted({_required_text(item, "target participant") for item in self.target_ids})
        )
        if not sources or not targets:
            raise DomainError("a possibilidade exige participantes de origem e destino")
        if set(sources) & set(targets):
            raise DomainError(
                "os identificadores de origem e destino não podem se repetir entre os lados"
            )
        confidence = _decimal(self.confidence, "confidence")
        if not Decimal("0") <= confidence <= Decimal("1"):
            raise DomainError("a confiança deve ficar entre zero e um")
        if self.status not in {MatchStatus.MATCHED, MatchStatus.SPLIT_MATCHED}:
            raise DomainError("o status da possibilidade deve descrever uma conciliação automática")
        if self.status is MatchStatus.MATCHED and (len(sources) != 1 or len(targets) != 1):
            raise DomainError(
                "possibilidades conciliadas exigem exatamente um participante de cada lado"
            )
        if self.status is MatchStatus.SPLIT_MATCHED and len(sources) == len(targets):
            raise DomainError(
                "conciliações em grupo exigem quantidades diferentes de "
                "participantes entre os lados"
            )
        object.__setattr__(self, "source_ids", sources)
        object.__setattr__(self, "target_ids", targets)
        object.__setattr__(self, "confidence", confidence)

    @property
    def participant_ids(self) -> tuple[str, ...]:
        return (*self.source_ids, *self.target_ids)


def deterministic_decision_id(
    status: MatchStatus,
    source_ids: tuple[str, ...],
    target_ids: tuple[str, ...],
    rule: RuleReference | None,
) -> str:
    payload = "|".join(
        (
            status.value,
            ",".join(sorted(source_ids)),
            ",".join(sorted(target_ids)),
            rule.rule_id if rule else "none",
            rule.version if rule else "none",
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    decision_id: str
    status: MatchStatus
    source_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    explanation: MatchExplanation
    rule: RuleReference | None = None
    confidence: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _required_text(self.decision_id, "decision_id"))
        sources = tuple(
            sorted({_required_text(item, "source participant") for item in self.source_ids})
        )
        targets = tuple(
            sorted({_required_text(item, "target participant") for item in self.target_ids})
        )
        if not sources and not targets:
            raise DomainError("a decisão exige pelo menos um participante")
        if set(sources) & set(targets):
            raise DomainError("os participantes da decisão não podem se repetir entre os lados")
        automatic = self.status in {MatchStatus.MATCHED, MatchStatus.SPLIT_MATCHED}
        if automatic and (self.rule is None or self.confidence is None):
            raise DomainError("decisões automáticas exigem regra e confiança")
        if self.confidence is not None:
            confidence = _decimal(self.confidence, "confidence")
            if not Decimal("0") <= confidence <= Decimal("1"):
                raise DomainError("a confiança deve ficar entre zero e um")
            object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "source_ids", sources)
        object.__setattr__(self, "target_ids", targets)

    @classmethod
    def from_candidate(cls, candidate: MatchCandidate) -> ReconciliationDecision:
        return cls(
            decision_id=deterministic_decision_id(
                candidate.status,
                candidate.source_ids,
                candidate.target_ids,
                candidate.rule,
            ),
            status=candidate.status,
            source_ids=candidate.source_ids,
            target_ids=candidate.target_ids,
            rule=candidate.rule,
            confidence=candidate.confidence,
            explanation=candidate.explanation,
        )

    @property
    def participant_ids(self) -> tuple[str, ...]:
        return (*self.source_ids, *self.target_ids)


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    run_id: str
    decisions: tuple[ReconciliationDecision, ...]
    counts: Mapping[MatchStatus, int] = field(init=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        ordered = tuple(sorted(self.decisions, key=lambda item: item.decision_id))
        participant_counts = Counter(
            participant for decision in ordered for participant in decision.participant_ids
        )
        repeated = sorted(
            participant for participant, count in participant_counts.items() if count > 1
        )
        if repeated:
            raise DomainError(f"há participantes em mais de uma decisão: {', '.join(repeated)}")
        counts = Counter(decision.status for decision in ordered)
        object.__setattr__(self, "decisions", ordered)
        object.__setattr__(self, "counts", MappingProxyType(dict(counts)))


_ALLOWED_TRANSITIONS: Mapping[RunStatus, frozenset[RunStatus]] = {
    RunStatus.PENDING: frozenset({RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.FAILED}),
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.FAILED}),
    RunStatus.RUNNING: frozenset({RunStatus.QUEUED, RunStatus.COMPLETED, RunStatus.FAILED}),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class ReconciliationRun:
    run_id: str
    dataset_a: DatasetFingerprint
    dataset_b: DatasetFingerprint
    rule_set: RuleReference
    normalization_version: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    idempotency_key: str

    def __post_init__(self) -> None:
        for name in (
            "run_id",
            "normalization_version",
            "correlation_id",
            "idempotency_key",
        ):
            object.__setattr__(self, name, _required_text(getattr(self, name), name))
        for name in ("created_at", "updated_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise DomainError(f"{_FIELD_LABELS[name]} deve incluir o fuso horário")
        if self.updated_at < self.created_at:
            raise DomainError("a data de atualização não pode ser anterior à data de criação")

    def transition(self, status: RunStatus, *, at: datetime | None = None) -> ReconciliationRun:
        if status not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidTransitionError(
                "não é possível alterar a execução do estado atual para o estado solicitado"
            )
        changed_at = at or datetime.now(UTC)
        if changed_at.tzinfo is None or changed_at.utcoffset() is None:
            raise DomainError("o horário da transição deve incluir o fuso horário")
        return replace(self, status=status, updated_at=changed_at)
