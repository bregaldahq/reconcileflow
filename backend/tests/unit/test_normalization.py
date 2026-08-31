from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from reconcileflow.domain.errors import MonetaryFloatError, NormalizationError
from reconcileflow.domain.models import DatasetFingerprint, DatasetSide
from reconcileflow.domain.normalization import (
    CanonicalMapping,
    derived_source_record_id,
    normalize_date,
    normalize_identifier,
    normalize_money,
    normalize_row,
    normalize_text,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234,56", Decimal("1234.56")),
        ("1234.56", Decimal("1234.56")),
        ("R$ 1.234,56", Decimal("1234.56")),
        ("(R$ 10,25)", Decimal("-10.25")),
        (1234, Decimal("1234.00")),
        (Decimal("9.9"), Decimal("9.90")),
    ],
)
def test_normalize_money_formats(raw: object, expected: Decimal) -> None:
    assert normalize_money(raw) == expected


def test_normalize_money_rejects_float_and_excess_scale() -> None:
    with pytest.raises(MonetaryFloatError):
        normalize_money(0.1)
    with pytest.raises(NormalizationError, match="duas casas decimais"):
        normalize_money("1.001")


@pytest.mark.parametrize("raw", ["abc", "R$", True, object()])
def test_normalize_money_rejects_invalid_values(raw: object) -> None:
    with pytest.raises(NormalizationError):
        normalize_money(raw)


def test_text_and_identifier_normalization() -> None:
    assert normalize_text("  Conta\u00a0   Azul ") == "Conta Azul"
    assert normalize_identifier("123.456.789-01") == "12345678901"
    assert normalize_identifier(" n/a ") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-03-05", date(2026, 3, 5)),
        ("05/03/2026", date(2026, 3, 5)),
        ("05-03-2026", date(2026, 3, 5)),
        (datetime(2026, 3, 5, 12, 0), date(2026, 3, 5)),
    ],
)
def test_normalize_date_supported_formats(raw: object, expected: date) -> None:
    assert normalize_date(raw) == expected


def test_normalize_date_rejects_guessing() -> None:
    with pytest.raises(NormalizationError, match="formato de data não aceito"):
        normalize_date("03/05/26")


def test_missing_source_id_is_deterministic() -> None:
    fingerprint = DatasetFingerprint.from_bytes(b"rows")
    assert derived_source_record_id(fingerprint, 2) == derived_source_record_id(fingerprint, 2)
    assert derived_source_record_id(fingerprint, 2) != derived_source_record_id(fingerprint, 3)


def test_normalize_row_builds_globally_scoped_id() -> None:
    mapping = CanonicalMapping(
        amount="Valor",
        currency=None,
        booking_date="Data",
        transaction_id="ID",
        document="CPF",
        reference="Ref",
    )
    transaction = normalize_row(
        {
            "Valor": "R$ 1.234,56",
            "Data": "05/03/2026",
            "ID": " tx-01 ",
            "CPF": "123.456.789-01",
            "Ref": "  invoice  7 ",
        },
        mapping=mapping,
        dataset_id="dataset-a",
        side=DatasetSide.A,
        fingerprint=DatasetFingerprint.from_bytes(b"file"),
        row_number=2,
    )
    assert transaction.transaction_id == "dataset-a:TX01"
    assert transaction.money.amount == Decimal("1234.56")
    assert transaction.document == "12345678901"
    assert transaction.reference == "INVOICE7"


def test_normalize_row_reports_missing_mapped_column() -> None:
    with pytest.raises(NormalizationError, match="coluna mapeada"):
        normalize_row(
            {},
            mapping=CanonicalMapping("amount", None, "date"),
            dataset_id="a",
            side=DatasetSide.A,
            fingerprint=DatasetFingerprint.from_bytes(b"a"),
            row_number=1,
        )
