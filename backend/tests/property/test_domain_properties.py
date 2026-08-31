from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from reconcileflow.domain.matching import (
    AmountDateToleranceConfig,
    AmountDateToleranceRule,
    BoundedSplitConfig,
    BoundedSplitRule,
    ExactCompositeRule,
    ReconciliationEngine,
)
from reconcileflow.domain.models import CanonicalTransaction, DatasetSide, MatchStatus, Money
from reconcileflow.domain.normalization import normalize_money


def transaction(
    transaction_id: str,
    side: DatasetSide,
    amount: str,
    *,
    reference: str = "INV100",
) -> CanonicalTransaction:
    dataset_id = "dataset-a" if side is DatasetSide.A else "dataset-b"
    return CanonicalTransaction(
        transaction_id=f"{dataset_id}:{transaction_id}",
        dataset_id=dataset_id,
        side=side,
        money=Money(Decimal(amount), "BRL"),
        booking_date=date(2026, 1, 15),
        source_record_id=transaction_id,
        document="12345678901",
        reference=reference,
    )


@pytest.mark.property
@given(st.integers(min_value=-1_000_000, max_value=1_000_000), st.integers(0, 99))
def test_invariant_money_string_round_trip(units: int, cents: int) -> None:
    sign = "-" if units < 0 else ""
    raw = f"{sign}{abs(units)}.{cents:02d}"
    assert normalize_money(raw) == Decimal(raw)


@pytest.mark.property
@given(order=st.permutations((0, 1, 2)))
def test_exact_result_is_input_order_independent(order: tuple[int, ...]) -> None:
    transactions = (
        transaction("source", DatasetSide.A, "10"),
        transaction("target-1", DatasetSide.B, "10"),
        transaction("target-2", DatasetSide.B, "10"),
    )
    baseline = ReconciliationEngine((ExactCompositeRule(),)).reconcile(
        run_id="run", transactions=transactions
    )
    permuted = ReconciliationEngine((ExactCompositeRule(),)).reconcile(
        run_id="run", transactions=tuple(transactions[index] for index in order)
    )
    assert permuted == baseline


@pytest.mark.property
@given(parts=st.lists(st.integers(min_value=1, max_value=500), min_size=2, max_size=4))
def test_split_matches_conserve_amount(parts: list[int]) -> None:
    source = transaction("source", DatasetSide.A, str(sum(parts)))
    targets = tuple(
        transaction(f"target-{index}", DatasetSide.B, str(amount))
        for index, amount in enumerate(parts)
    )
    engine = ReconciliationEngine(
        (
            BoundedSplitRule(
                BoundedSplitConfig(
                    Decimal("0"),
                    0,
                    max_group_size=4,
                    max_candidate_pool=8,
                    max_combinations=500,
                )
            ),
        )
    )
    result = engine.reconcile(run_id="run", transactions=(source, *targets))
    split = [
        decision for decision in result.decisions if decision.status is MatchStatus.SPLIT_MATCHED
    ]
    if split:
        assert sum((item.money.amount for item in targets), Decimal("0")) == source.money.amount


@pytest.mark.property
def test_rule_pipeline_is_stable_under_repeated_random_shuffles() -> None:
    transactions = [
        transaction("a-exact", DatasetSide.A, "100"),
        transaction("b-exact", DatasetSide.B, "100"),
        transaction("a-split", DatasetSide.A, "500", reference="SPLIT"),
        transaction("b-split-1", DatasetSide.B, "300", reference="SPLIT"),
        transaction("b-split-2", DatasetSide.B, "200", reference="SPLIT"),
    ]
    engine = ReconciliationEngine(
        (
            ExactCompositeRule(),
            AmountDateToleranceRule(AmountDateToleranceConfig(Decimal("1"), 1)),
            BoundedSplitRule(BoundedSplitConfig(Decimal("0"), 0)),
        )
    )
    baseline = engine.reconcile(run_id="run", transactions=transactions)
    rng = random.Random(42)  # noqa: S311 - deterministic test permutation, not security.
    for _ in range(20):
        rng.shuffle(transactions)
        assert engine.reconcile(run_id="run", transactions=transactions) == baseline
