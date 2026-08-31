from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from reconcileflow.domain.matching import BoundedSplitConfig, BoundedSplitRule
from reconcileflow.domain.models import CanonicalTransaction, DatasetSide, Money


@pytest.mark.performance
def test_split_candidate_search_stays_within_regression_budget(benchmark) -> None:
    source = CanonicalTransaction(
        "a:source",
        "a",
        DatasetSide.A,
        Money(Decimal("1000"), "BRL"),
        date(2026, 1, 1),
        "source",
        "DOC",
        "REF",
    )
    targets = tuple(
        CanonicalTransaction(
            f"b:{index}",
            "b",
            DatasetSide.B,
            Money(Decimal(index * 10), "BRL"),
            date(2026, 1, 1),
            str(index),
            "DOC",
            "REF",
        )
        for index in range(1, 21)
    )
    rule = BoundedSplitRule(
        BoundedSplitConfig(
            Decimal("0"), 0, max_group_size=4, max_candidate_pool=20, max_combinations=5000
        )
    )
    batch = benchmark(rule.candidates, (source,), targets)
    assert len(batch.candidates) <= 5000
