from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from reconcileflow.adapters.ingestion import TabularDatasetParser
from reconcileflow.application.services import build_engine
from reconcileflow.bootstrap import DEFAULT_PROFILE
from reconcileflow.domain.models import DatasetSide, MatchStatus
from reconcileflow.domain.normalization import CanonicalMapping, normalize_row


@pytest.mark.golden
def test_demo_fixtures_cover_the_portfolio_walkthrough() -> None:
    root = Path(__file__).parents[3]
    parser = TabularDatasetParser()
    mapping = CanonicalMapping(
        amount="amount",
        currency="currency",
        booking_date="booking_date",
        transaction_id="transaction_id",
        document="document",
        reference="reference",
    )
    transactions = []
    for side, filename, dataset_id in (
        (DatasetSide.A, "ledger-a.csv", "demo-a"),
        (DatasetSide.B, "settlement-b.csv", "demo-b"),
    ):
        content = (root / "fixtures" / "demo" / filename).read_bytes()
        parsed = parser.parse(filename=filename, content_type="text/csv", content=content)
        transactions.extend(
            normalize_row(
                row,
                mapping=mapping,
                dataset_id=dataset_id,
                side=side,
                fingerprint=parsed.fingerprint,
                row_number=row_number,
            )
            for row_number, row in enumerate(parsed.rows, start=2)
        )

    result = build_engine(DEFAULT_PROFILE).reconcile(run_id="demo-run", transactions=transactions)

    assert result.counts == {
        MatchStatus.MATCHED: 2,
        MatchStatus.SPLIT_MATCHED: 2,
        MatchStatus.UNMATCHED: 2,
        MatchStatus.AMBIGUOUS: 1,
        MatchStatus.DUPLICATE: 1,
    }
    matched_rules = {
        decision.rule.rule_id for decision in result.decisions if decision.rule is not None
    }
    assert {"exact_composite", "amount_date_tolerance", "bounded_split"} <= matched_rules
    for decision in result.decisions:
        if decision.status is not MatchStatus.SPLIT_MATCHED:
            continue
        sources = [item for item in transactions if item.transaction_id in decision.source_ids]
        targets = [item for item in transactions if item.transaction_id in decision.target_ids]
        source_total = sum((item.money.amount for item in sources), Decimal("0"))
        target_total = sum((item.money.amount for item in targets), Decimal("0"))
        assert source_total == target_total
