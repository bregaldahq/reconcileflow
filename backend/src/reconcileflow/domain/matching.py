"""Deterministic, explainable reconciliation rules and pipeline."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import combinations
from typing import Protocol

from reconcileflow.domain.errors import DomainError, MonetaryFloatError
from reconcileflow.domain.models import (
    CanonicalTransaction,
    DatasetSide,
    MatchCandidate,
    MatchExplanation,
    MatchStatus,
    ReconciliationDecision,
    ReconciliationResult,
    RuleReference,
    deterministic_decision_id,
)

_MIN_SPLIT_GROUP_SIZE = 2


def _validated_decimal(value: object, name: str) -> Decimal:
    label = "a tolerância de valor" if name == "amount_tolerance" else name
    if isinstance(value, float):
        raise MonetaryFloatError(f"{label} não pode ser um número binário de ponto flutuante")
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise DomainError(f"{label} deve ser um Decimal finito e não negativo")
    return value


@dataclass(frozen=True, slots=True)
class CandidateBatch:
    candidates: tuple[MatchCandidate, ...]
    limited_participant_ids: tuple[str, ...] = ()


class MatchingRule(Protocol):
    reference: RuleReference

    def candidates(
        self,
        sources: Sequence[CanonicalTransaction],
        targets: Sequence[CanonicalTransaction],
    ) -> CandidateBatch: ...


@dataclass(frozen=True, slots=True)
class ExactCompositeConfig:
    fields: tuple[str, ...] = ("currency", "amount", "date", "document", "reference")

    def __post_init__(self) -> None:
        if not self.fields or len(set(self.fields)) != len(self.fields):
            raise DomainError("os campos exatos não podem estar vazios nem se repetir")


@dataclass(frozen=True, slots=True)
class ExactCompositeRule:
    config: ExactCompositeConfig = field(default_factory=ExactCompositeConfig)
    reference: RuleReference = field(default_factory=lambda: RuleReference("exact_composite", "1"))

    def candidates(
        self,
        sources: Sequence[CanonicalTransaction],
        targets: Sequence[CanonicalTransaction],
    ) -> CandidateBatch:
        matches: list[MatchCandidate] = []
        for source in sorted(sources, key=lambda item: item.transaction_id):
            source_values = tuple(source.field_value(field) for field in self.config.fields)
            if any(value is None for value in source_values):
                continue
            for target in sorted(targets, key=lambda item: item.transaction_id):
                target_values = tuple(target.field_value(field) for field in self.config.fields)
                if source_values != target_values:
                    continue
                evidence = tuple(f"{field}: igual" for field in self.config.fields)
                matches.append(
                    MatchCandidate(
                        source_ids=(source.transaction_id,),
                        target_ids=(target.transaction_id,),
                        rule=self.reference,
                        confidence=Decimal("1"),
                        explanation=MatchExplanation(
                            "Todos os campos canônicos configurados são iguais.", evidence
                        ),
                    )
                )
        return CandidateBatch(tuple(matches))


@dataclass(frozen=True, slots=True)
class AmountDateToleranceConfig:
    amount_tolerance: Decimal
    date_tolerance_days: int
    identity_fields: tuple[str, ...] = ("currency", "document")

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "amount_tolerance",
            _validated_decimal(self.amount_tolerance, "amount_tolerance"),
        )
        if self.date_tolerance_days < 0:
            raise DomainError("a tolerância de dias não pode ser negativa")
        if len(set(self.identity_fields)) != len(self.identity_fields):
            raise DomainError("os campos de identidade não podem se repetir")


def _distance_confidence(
    amount_delta: Decimal,
    amount_tolerance: Decimal,
    date_delta: int,
    date_tolerance: int,
) -> Decimal:
    amount_score = (
        Decimal("1") if amount_tolerance == 0 else Decimal("1") - (amount_delta / amount_tolerance)
    )
    date_score = (
        Decimal("1")
        if date_tolerance == 0
        else Decimal("1") - (Decimal(date_delta) / Decimal(date_tolerance))
    )
    return ((amount_score + date_score) / Decimal("2")).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_EVEN
    )


def _identity_equal(
    left: CanonicalTransaction,
    right: CanonicalTransaction,
    fields: tuple[str, ...],
) -> bool:
    for field_name in fields:
        left_value = left.field_value(field_name)
        right_value = right.field_value(field_name)
        if left_value is None or right_value is None or left_value != right_value:
            return False
    return True


@dataclass(frozen=True, slots=True)
class AmountDateToleranceRule:
    config: AmountDateToleranceConfig
    reference: RuleReference = field(
        default_factory=lambda: RuleReference("amount_date_tolerance", "1")
    )

    def candidates(
        self,
        sources: Sequence[CanonicalTransaction],
        targets: Sequence[CanonicalTransaction],
    ) -> CandidateBatch:
        matches: list[MatchCandidate] = []
        for source in sorted(sources, key=lambda item: item.transaction_id):
            for target in sorted(targets, key=lambda item: item.transaction_id):
                if not _identity_equal(source, target, self.config.identity_fields):
                    continue
                amount_delta = abs(source.money.amount - target.money.amount)
                date_delta = abs((source.booking_date - target.booking_date).days)
                if (
                    amount_delta > self.config.amount_tolerance
                    or date_delta > self.config.date_tolerance_days
                ):
                    continue
                confidence = _distance_confidence(
                    amount_delta,
                    self.config.amount_tolerance,
                    date_delta,
                    self.config.date_tolerance_days,
                )
                evidence = (
                    f"diferença de valor {amount_delta} <= {self.config.amount_tolerance}",
                    f"diferença de data {date_delta}d <= {self.config.date_tolerance_days}d",
                    *(f"{field}: igual" for field in self.config.identity_fields),
                )
                matches.append(
                    MatchCandidate(
                        source_ids=(source.transaction_id,),
                        target_ids=(target.transaction_id,),
                        rule=self.reference,
                        confidence=confidence,
                        explanation=MatchExplanation(
                            "O valor e a data estão dentro dos limites configurados.", evidence
                        ),
                    )
                )
        return CandidateBatch(tuple(matches))


@dataclass(frozen=True, slots=True)
class BoundedSplitConfig:
    amount_tolerance: Decimal
    date_tolerance_days: int
    max_group_size: int = 4
    max_candidate_pool: int = 20
    max_combinations: int = 5000
    identity_fields: tuple[str, ...] = ("currency", "document")

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "amount_tolerance",
            _validated_decimal(self.amount_tolerance, "amount_tolerance"),
        )
        if self.date_tolerance_days < 0:
            raise DomainError("a tolerância de dias não pode ser negativa")
        if self.max_group_size < _MIN_SPLIT_GROUP_SIZE:
            raise DomainError("o tamanho máximo do grupo deve ser de pelo menos dois")
        if self.max_candidate_pool < self.max_group_size:
            raise DomainError(
                "o limite de possibilidades deve ser igual ou maior que o tamanho máximo do grupo"
            )
        if self.max_combinations < 1:
            raise DomainError("o número máximo de combinações deve ser positivo")


@dataclass(frozen=True, slots=True)
class BoundedSplitRule:
    config: BoundedSplitConfig
    reference: RuleReference = field(default_factory=lambda: RuleReference("bounded_split", "1"))

    def _pool(
        self,
        anchor: CanonicalTransaction,
        others: Sequence[CanonicalTransaction],
    ) -> tuple[CanonicalTransaction, ...]:
        eligible = [
            item
            for item in others
            if _identity_equal(anchor, item, self.config.identity_fields)
            and abs((anchor.booking_date - item.booking_date).days)
            <= self.config.date_tolerance_days
        ]
        return tuple(sorted(eligible, key=lambda item: item.transaction_id))

    def _direction_candidates(
        self,
        anchors: Sequence[CanonicalTransaction],
        others: Sequence[CanonicalTransaction],
        *,
        anchor_is_source: bool,
    ) -> tuple[list[MatchCandidate], set[str]]:
        matches: list[MatchCandidate] = []
        limited: set[str] = set()
        inspected = 0
        ordered_anchors = tuple(sorted(anchors, key=lambda item: item.transaction_id))
        for anchor_index, anchor in enumerate(ordered_anchors):
            pool = self._pool(anchor, others)
            if len(pool) > self.config.max_candidate_pool:
                limited.add(anchor.transaction_id)
                pool = pool[: self.config.max_candidate_pool]
            for group_size in range(
                _MIN_SPLIT_GROUP_SIZE, min(self.config.max_group_size, len(pool)) + 1
            ):
                for group in combinations(pool, group_size):
                    inspected += 1
                    if inspected > self.config.max_combinations:
                        limited.update(
                            item.transaction_id for item in ordered_anchors[anchor_index:]
                        )
                        return matches, limited
                    group_amount = sum((item.money.amount for item in group), start=Decimal("0"))
                    amount_delta = abs(anchor.money.amount - group_amount)
                    if amount_delta > self.config.amount_tolerance:
                        continue
                    date_delta = max(
                        abs((anchor.booking_date - item.booking_date).days) for item in group
                    )
                    confidence = _distance_confidence(
                        amount_delta,
                        self.config.amount_tolerance,
                        date_delta,
                        self.config.date_tolerance_days,
                    )
                    source_ids = (
                        (anchor.transaction_id,)
                        if anchor_is_source
                        else tuple(item.transaction_id for item in group)
                    )
                    target_ids = (
                        tuple(item.transaction_id for item in group)
                        if anchor_is_source
                        else (anchor.transaction_id,)
                    )
                    matches.append(
                        MatchCandidate(
                            source_ids=source_ids,
                            target_ids=target_ids,
                            rule=self.reference,
                            confidence=confidence,
                            status=MatchStatus.SPLIT_MATCHED,
                            explanation=MatchExplanation(
                                "Um grupo dentro dos limites conserva o valor conciliado.",
                                (
                                    (
                                        f"diferença de valor {amount_delta}"
                                        f" <= {self.config.amount_tolerance}"
                                    ),
                                    (
                                        f"tamanho do grupo {group_size}"
                                        f" <= {self.config.max_group_size}"
                                    ),
                                    (
                                        f"intervalo de datas {date_delta}d"
                                        f" <= {self.config.date_tolerance_days}d"
                                    ),
                                    *(f"{field}: igual" for field in self.config.identity_fields),
                                ),
                            ),
                        )
                    )
        return matches, limited

    def candidates(
        self,
        sources: Sequence[CanonicalTransaction],
        targets: Sequence[CanonicalTransaction],
    ) -> CandidateBatch:
        one_to_many, one_limited = self._direction_candidates(
            sources, targets, anchor_is_source=True
        )
        many_to_one, many_limited = self._direction_candidates(
            targets, sources, anchor_is_source=False
        )
        ordered = sorted(
            (*one_to_many, *many_to_one),
            key=lambda item: (item.participant_ids, -item.confidence),
        )
        return CandidateBatch(tuple(ordered), tuple(sorted(one_limited | many_limited)))


def _overlap_components(candidates: Sequence[MatchCandidate]) -> list[list[MatchCandidate]]:
    by_participant: dict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        for participant in candidate.participant_ids:
            by_participant[participant].append(index)
    unseen = set(range(len(candidates)))
    components: list[list[MatchCandidate]] = []
    while unseen:
        first = min(unseen)
        queue = deque([first])
        component_indexes: set[int] = set()
        while queue:
            index = queue.popleft()
            if index in component_indexes:
                continue
            component_indexes.add(index)
            unseen.discard(index)
            for participant in candidates[index].participant_ids:
                queue.extend(by_participant[participant])
        components.append([candidates[index] for index in sorted(component_indexes)])
    return components


def _ambiguous_decision(candidates: Sequence[MatchCandidate]) -> ReconciliationDecision:
    source_ids = tuple(sorted({item for candidate in candidates for item in candidate.source_ids}))
    target_ids = tuple(sorted({item for candidate in candidates for item in candidate.target_ids}))
    rule = candidates[0].rule
    confidence = candidates[0].confidence
    evidence = tuple(
        (
            f"possibilidade origens={','.join(candidate.source_ids)}"
            f" destinos={','.join(candidate.target_ids)}"
        )
        for candidate in sorted(candidates, key=lambda item: item.participant_ids)
    )
    return ReconciliationDecision(
        decision_id=deterministic_decision_id(MatchStatus.AMBIGUOUS, source_ids, target_ids, rule),
        status=MatchStatus.AMBIGUOUS,
        source_ids=source_ids,
        target_ids=target_ids,
        rule=rule,
        confidence=confidence,
        explanation=MatchExplanation(
            "Há mais de uma possibilidade igualmente válida; a decisão precisa de revisão.",
            evidence,
        ),
    )


def resolve_candidates(candidates: Sequence[MatchCandidate]) -> tuple[ReconciliationDecision, ...]:
    remaining = list(candidates)
    decisions: list[ReconciliationDecision] = []
    while remaining:
        best_confidence = max(candidate.confidence for candidate in remaining)
        best = [candidate for candidate in remaining if candidate.confidence == best_confidence]
        consumed: set[str] = set()
        for component in _overlap_components(best):
            if len(component) == 1:
                decision = ReconciliationDecision.from_candidate(component[0])
            else:
                decision = _ambiguous_decision(component)
            decisions.append(decision)
            consumed.update(decision.participant_ids)
        remaining = [
            candidate
            for candidate in remaining
            if not consumed.intersection(candidate.participant_ids)
        ]
    return tuple(sorted(decisions, key=lambda item: item.decision_id))


def _duplicate_decisions(
    transactions: Sequence[CanonicalTransaction],
) -> tuple[ReconciliationDecision, ...]:
    grouped: dict[tuple[object, ...], list[CanonicalTransaction]] = defaultdict(list)
    for transaction in transactions:
        grouped[transaction.duplicate_key()].append(transaction)
    decisions: list[ReconciliationDecision] = []
    for group in grouped.values():
        if len(group) < _MIN_SPLIT_GROUP_SIZE:
            continue
        source_ids = tuple(
            sorted(item.transaction_id for item in group if item.side is DatasetSide.A)
        )
        target_ids = tuple(
            sorted(item.transaction_id for item in group if item.side is DatasetSide.B)
        )
        decisions.append(
            ReconciliationDecision(
                decision_id=deterministic_decision_id(
                    MatchStatus.DUPLICATE, source_ids, target_ids, None
                ),
                status=MatchStatus.DUPLICATE,
                source_ids=source_ids,
                target_ids=target_ids,
                explanation=MatchExplanation(
                    "Existem registros repetidos no mesmo lado da conciliação.",
                    (f"quantidade de duplicados {len(group)}",),
                ),
            )
        )
    return tuple(decisions)


@dataclass(frozen=True, slots=True)
class ReconciliationEngine:
    rules: tuple[MatchingRule, ...]

    def __post_init__(self) -> None:
        references = [(rule.reference.rule_id, rule.reference.version) for rule in self.rules]
        if len(references) != len(set(references)):
            raise DomainError("o fluxo de conciliação contém referências de regra repetidas")

    def reconcile(
        self,
        *,
        run_id: str,
        transactions: Sequence[CanonicalTransaction],
    ) -> ReconciliationResult:
        by_id = {item.transaction_id: item for item in transactions}
        if len(by_id) != len(transactions):
            raise DomainError("os identificadores das transações devem ser globalmente únicos")
        sources = tuple(item for item in transactions if item.side is DatasetSide.A)
        targets = tuple(item for item in transactions if item.side is DatasetSide.B)
        decisions = list(_duplicate_decisions(sources)) + list(_duplicate_decisions(targets))
        consumed = {
            participant for decision in decisions for participant in decision.participant_ids
        }

        for rule in self.rules:
            available_sources = tuple(
                item for item in sources if item.transaction_id not in consumed
            )
            available_targets = tuple(
                item for item in targets if item.transaction_id not in consumed
            )
            batch = rule.candidates(available_sources, available_targets)
            resolved = resolve_candidates(batch.candidates)
            decisions.extend(resolved)
            consumed.update(
                participant for decision in resolved for participant in decision.participant_ids
            )
            for participant in batch.limited_participant_ids:
                if participant in consumed:
                    continue
                transaction = by_id[participant]
                source_ids = (participant,) if transaction.side is DatasetSide.A else ()
                target_ids = (participant,) if transaction.side is DatasetSide.B else ()
                decision = ReconciliationDecision(
                    decision_id=deterministic_decision_id(
                        MatchStatus.MANUAL_REVIEW, source_ids, target_ids, rule.reference
                    ),
                    status=MatchStatus.MANUAL_REVIEW,
                    source_ids=source_ids,
                    target_ids=target_ids,
                    rule=rule.reference,
                    explanation=MatchExplanation(
                        "A busca de possibilidades atingiu o limite de segurança configurado.",
                        ("limite da busca restrita atingido",),
                    ),
                )
                decisions.append(decision)
                consumed.add(participant)

        for transaction in sorted(transactions, key=lambda item: item.transaction_id):
            if transaction.transaction_id in consumed:
                continue
            source_ids = (transaction.transaction_id,) if transaction.side is DatasetSide.A else ()
            target_ids = (transaction.transaction_id,) if transaction.side is DatasetSide.B else ()
            decisions.append(
                ReconciliationDecision(
                    decision_id=deterministic_decision_id(
                        MatchStatus.UNMATCHED, source_ids, target_ids, None
                    ),
                    status=MatchStatus.UNMATCHED,
                    source_ids=source_ids,
                    target_ids=target_ids,
                    explanation=MatchExplanation(
                        "Nenhuma regra automática configurada encontrou uma possibilidade.",
                        ("todas as regras configuradas foram avaliadas",),
                    ),
                )
            )
        return ReconciliationResult(run_id=run_id, decisions=tuple(decisions))
