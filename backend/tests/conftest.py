from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from reconcileflow.domain.models import CanonicalTransaction, DatasetSide, Money


@pytest.fixture
def transaction_factory():
    def factory(
        transaction_id: str,
        side: DatasetSide,
        amount: str,
        *,
        booking_date: date = date(2026, 1, 15),
        document: str | None = "12345678901",
        reference: str | None = "INV100",
    ) -> CanonicalTransaction:
        dataset_id = "dataset-a" if side is DatasetSide.A else "dataset-b"
        return CanonicalTransaction(
            transaction_id=f"{dataset_id}:{transaction_id}",
            dataset_id=dataset_id,
            side=side,
            money=Money(Decimal(amount), "BRL"),
            booking_date=booking_date,
            source_record_id=transaction_id,
            document=document,
            reference=reference,
        )

    return factory
