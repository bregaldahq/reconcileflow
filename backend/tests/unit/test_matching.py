from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from reconcileflow.domain.errors import DomainError, MonetaryFloatError
from reconcileflow.domain.matching import (
    AmountDateToleranceConfig,
    AmountDateToleranceRule,
    BoundedSplitConfig,
    BoundedSplitRule,
    ExactCompositeConfig,
    ExactCompositeRule,
    ReconciliationEngine,
)
from reconcileflow.domain.models import DatasetSide, MatchStatus


def test_unique_exact_candidate_is_matched_with_explanation(transaction_factory) -> None:
    source = transaction_factory("1", DatasetSide.A, "100")
    target = transaction_factory("1", DatasetSide.B, "100")
    result = ReconciliationEngine((ExactCompositeRule(),)).reconcile(
        run_id="run", transactions=(target, source)
    )
    assert len(result.decisions) == 1
    decision = result.decisions[0]
    assert decision.status is MatchStatus.MATCHED
    assert decision.rule is not None
    assert decision.rule.rule_id == "exact_composite"
    assert decision.confidence == Decimal("1")
    assert "amount: igual" in decision.explanation.evidence


def test_no_candidate_emits_unmatched_for_each_side(transaction_factory) -> None:
    source = transaction_factory("1", DatasetSide.A, "100")
    target = transaction_factory("1", DatasetSide.B, "101")
    result = ReconciliationEngine((ExactCompositeRule(),)).reconcile(
        run_id="run", transactions=(source, target)
    )
    assert result.counts[MatchStatus.UNMATCHED] == 2


def test_equal_exact_candidates_are_ambiguous(transaction_factory) -> None:
    source = transaction_factory("1", DatasetSide.A, "100")
    target_1 = transaction_factory("1", DatasetSide.B, "100", reference="INV-1")
    target_2 = transaction_factory("2", DatasetSide.B, "100", reference="INV-2")
    result = ReconciliationEngine(
        (ExactCompositeRule(ExactCompositeConfig(("currency", "amount", "date", "document"))),)
    ).reconcile(run_id="run", transactions=(source, target_1, target_2))
    assert result.counts[MatchStatus.AMBIGUOUS] == 1
    decision = next(item for item in result.decisions if item.status is MatchStatus.AMBIGUOUS)
    assert decision.target_ids == tuple(sorted((target_1.transaction_id, target_2.transaction_id)))


def test_same_side_canonical_duplicates_are_removed_before_matching(transaction_factory) -> None:
    source_1 = transaction_factory("1", DatasetSide.A, "100")
    source_2 = transaction_factory("2", DatasetSide.A, "100")
    target = transaction_factory("1", DatasetSide.B, "100")
    result = ReconciliationEngine((ExactCompositeRule(),)).reconcile(
        run_id="run", transactions=(source_1, source_2, target)
    )
    assert result.counts[MatchStatus.DUPLICATE] == 1
    assert result.counts[MatchStatus.UNMATCHED] == 1


def test_tolerance_rule_includes_boundary_and_calculates_confidence(transaction_factory) -> None:
    source = transaction_factory("1", DatasetSide.A, "100", booking_date=date(2026, 1, 15))
    target = transaction_factory("1", DatasetSide.B, "100.50", booking_date=date(2026, 1, 17))
    rule = AmountDateToleranceRule(AmountDateToleranceConfig(Decimal("0.50"), 2))
    result = ReconciliationEngine((rule,)).reconcile(run_id="run", transactions=(source, target))
    decision = result.decisions[0]
    assert decision.status is MatchStatus.MATCHED
    assert decision.confidence == Decimal("0.000000")
    assert "diferença de valor 0.50 <= 0.50" in decision.explanation.evidence


def test_tolerance_prefers_unique_higher_confidence(transaction_factory) -> None:
    source = transaction_factory("1", DatasetSide.A, "100")
    best = transaction_factory("best", DatasetSide.B, "100.01")
    lower = transaction_factory("lower", DatasetSide.B, "100.50")
    rule = AmountDateToleranceRule(AmountDateToleranceConfig(Decimal("1"), 0))
    result = ReconciliationEngine((rule,)).reconcile(
        run_id="run", transactions=(source, lower, best)
    )
    matched = next(item for item in result.decisions if item.status is MatchStatus.MATCHED)
    assert matched.target_ids == (best.transaction_id,)
    assert result.counts[MatchStatus.UNMATCHED] == 1


def test_tolerance_rejects_float_configuration() -> None:
    with pytest.raises(MonetaryFloatError):
        AmountDateToleranceConfig(0.5, 1)  # type: ignore[arg-type]


def test_exact_config_rejects_duplicate_fields() -> None:
    with pytest.raises(DomainError):
        ExactCompositeConfig(("amount", "amount"))


def test_one_to_many_split_conserves_amount(transaction_factory) -> None:
    source = transaction_factory("source", DatasetSide.A, "1000")
    targets = (
        transaction_factory("t500", DatasetSide.B, "500"),
        transaction_factory("t300", DatasetSide.B, "300"),
        transaction_factory("t200", DatasetSide.B, "200"),
    )
    rule = BoundedSplitRule(BoundedSplitConfig(Decimal("0"), 0))
    result = ReconciliationEngine((rule,)).reconcile(run_id="run", transactions=(source, *targets))
    decision = result.decisions[0]
    assert decision.status is MatchStatus.SPLIT_MATCHED
    assert sum((item.money.amount for item in targets), Decimal("0")) == source.money.amount
    assert decision.target_ids == tuple(sorted(item.transaction_id for item in targets))


def test_many_to_one_split_is_supported(transaction_factory) -> None:
    sources = (
        transaction_factory("s700", DatasetSide.A, "700"),
        transaction_factory("s300", DatasetSide.A, "300"),
    )
    target = transaction_factory("target", DatasetSide.B, "1000")
    result = ReconciliationEngine(
        (BoundedSplitRule(BoundedSplitConfig(Decimal("0"), 0)),)
    ).reconcile(run_id="run", transactions=(*sources, target))
    decision = result.decisions[0]
    assert decision.status is MatchStatus.SPLIT_MATCHED
    assert len(decision.source_ids) == 2
    assert decision.target_ids == (target.transaction_id,)


def test_equal_split_combinations_are_ambiguous(transaction_factory) -> None:
    source = transaction_factory("source", DatasetSide.A, "1000")
    targets = (
        transaction_factory("t1", DatasetSide.B, "600", reference="T1"),
        transaction_factory("t2", DatasetSide.B, "400", reference="T2"),
        transaction_factory("t3", DatasetSide.B, "600", reference="T3"),
        transaction_factory("t4", DatasetSide.B, "400", reference="T4"),
    )
    result = ReconciliationEngine(
        (BoundedSplitRule(BoundedSplitConfig(Decimal("0"), 0)),)
    ).reconcile(run_id="run", transactions=(source, *targets))
    assert result.counts[MatchStatus.AMBIGUOUS] == 1


def test_split_search_limit_routes_anchor_to_manual_review(transaction_factory) -> None:
    source = transaction_factory("source", DatasetSide.A, "1000")
    targets = tuple(
        transaction_factory(f"t{index}", DatasetSide.B, str(index * 10)) for index in range(1, 8)
    )
    rule = BoundedSplitRule(
        BoundedSplitConfig(
            Decimal("0"), 0, max_group_size=4, max_candidate_pool=7, max_combinations=1
        )
    )
    result = ReconciliationEngine((rule,)).reconcile(run_id="run", transactions=(source, *targets))
    assert result.counts[MatchStatus.MANUAL_REVIEW] >= 1


def test_split_limit_marks_every_uninspected_anchor(transaction_factory) -> None:
    sources = (
        transaction_factory("source-1", DatasetSide.A, "1000"),
        transaction_factory("source-2", DatasetSide.A, "2000"),
    )
    targets = tuple(
        transaction_factory(f"target-{index}", DatasetSide.B, str(index * 10))
        for index in range(1, 4)
    )
    rule = BoundedSplitRule(
        BoundedSplitConfig(
            Decimal("0"), 0, max_group_size=2, max_candidate_pool=3, max_combinations=1
        )
    )

    batch = rule.candidates(sources, targets)

    assert {item.transaction_id for item in sources} <= set(batch.limited_participant_ids)


def test_pipeline_does_not_reuse_participants(transaction_factory) -> None:
    source = transaction_factory("source", DatasetSide.A, "100")
    target = transaction_factory("target", DatasetSide.B, "100")
    engine = ReconciliationEngine(
        (
            ExactCompositeRule(ExactCompositeConfig(("currency", "amount"))),
            AmountDateToleranceRule(AmountDateToleranceConfig(Decimal("1"), 1)),
        )
    )
    result = engine.reconcile(run_id="run", transactions=(source, target))
    assert len(result.decisions) == 1
