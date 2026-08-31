from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from reconcileflow.domain.matching import (
    ExactCompositeConfig,
    ExactCompositeRule,
    ReconciliationEngine,
)
from reconcileflow.domain.models import CanonicalTransaction, DatasetSide, MatchStatus, Money


@pytest.mark.golden
def test_exact_ambiguous_golden_scenario() -> None:
    fixture_path = Path(__file__).parents[3] / "fixtures" / "golden" / "exact_ambiguous.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    transactions = tuple(
        CanonicalTransaction(
            transaction_id=item["id"],
            dataset_id=item["dataset"],
            side=DatasetSide(item["side"]),
            money=Money(Decimal(item["amount"]), "BRL"),
            booking_date=date.fromisoformat(item["date"]),
            source_record_id=item["id"].split(":", maxsplit=1)[1],
            document=item["document"],
            reference=item["reference"],
        )
        for item in payload["transactions"]
    )
    rule = ExactCompositeRule(ExactCompositeConfig(("currency", "amount", "date", "document")))
    result = ReconciliationEngine((rule,)).reconcile(
        run_id=payload["run_id"], transactions=transactions
    )
    counts = {status.value: count for status, count in result.counts.items()}
    assert counts == payload["expected"]
    decision = result.decisions[0]
    assert decision.status is MatchStatus.AMBIGUOUS
    assert decision.explanation.evidence == (
        "possibilidade origens=dataset-a:S1 destinos=dataset-b:T1",
        "possibilidade origens=dataset-a:S1 destinos=dataset-b:T2",
    )
