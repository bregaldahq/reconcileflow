"""Versioned deterministic normalization for source records."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from reconcileflow.domain.errors import MonetaryFloatError, NormalizationError
from reconcileflow.domain.models import (
    CanonicalTransaction,
    DatasetFingerprint,
    DatasetSide,
    Money,
)

NORMALIZATION_VERSION = "br-v1"
_EMPTY_MARKERS = frozenset({"", "-", "--", "n/a", "na", "null", "none"})
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")
_NON_IDENTIFIER = re.compile(r"[^0-9A-Za-z]+")
_MONEY_PATTERN = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_MONEY_DECIMAL_PLACES = 2


@dataclass(frozen=True, slots=True)
class CanonicalMapping:
    amount: str
    currency: str | None
    booking_date: str
    transaction_id: str | None = None
    source_record_id: str | None = None
    document: str | None = None
    reference: str | None = None
    default_currency: str = "BRL"

    def __post_init__(self) -> None:
        if not self.amount.strip() or not self.booking_date.strip():
            raise NormalizationError("os mapeamentos de valor e data são obrigatórios")
        if self.currency is None and not self.default_currency.strip():
            raise NormalizationError("o mapeamento de moeda ou uma moeda padrão é obrigatório")


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):  # NaN from tabular parsers is an empty value, not domain money.
            return None
        raise NormalizationError(
            "números binários de ponto flutuante não são aceitos como texto canônico"
        )
    text = unicodedata.normalize("NFKC", str(value))
    collapsed = " ".join(text.replace("\u00a0", " ").split())
    if collapsed.casefold() in _EMPTY_MARKERS:
        return None
    return collapsed


def normalize_identifier(value: object) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    identifier = _NON_IDENTIFIER.sub("", text).upper()
    return identifier or None


def _standardize_monetary_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    negative_parentheses = normalized.startswith("(") and normalized.endswith(")")
    if negative_parentheses:
        normalized = normalized[1:-1]
    normalized = re.sub(r"(?i)\b(?:BRL|USD|EUR)\b", "", normalized)
    normalized = normalized.replace("R$", "").replace("$", "").replace("€", "")
    normalized = normalized.replace("\u00a0", "").replace(" ", "")
    if not normalized:
        raise NormalizationError("o valor monetário está vazio")

    comma = normalized.rfind(",")
    point = normalized.rfind(".")
    if comma >= 0 and point >= 0:
        decimal_separator = "," if comma > point else "."
        grouping_separator = "." if decimal_separator == "," else ","
        normalized = normalized.replace(grouping_separator, "")
        normalized = normalized.replace(decimal_separator, ".")
    elif comma >= 0:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", "")

    if negative_parentheses:
        normalized = f"-{normalized}"
    if not _MONEY_PATTERN.fullmatch(normalized):
        raise NormalizationError(f"formato monetário inválido: {value!r}")
    return normalized


def normalize_money(value: object) -> Decimal:
    if isinstance(value, float):
        raise MonetaryFloatError(
            "números binários de ponto flutuante não podem entrar na normalização monetária"
        )
    if isinstance(value, bool):
        raise NormalizationError("um valor booleano não é um valor monetário")
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        try:
            amount = Decimal(_standardize_monetary_text(value))
        except InvalidOperation as error:
            raise NormalizationError(f"valor monetário inválido: {value!r}") from error
    else:
        raise NormalizationError("o valor recebido não possui um tipo monetário aceito")
    if not amount.is_finite():
        raise NormalizationError("o valor monetário deve ser finito")
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -_MONEY_DECIMAL_PLACES:
        raise NormalizationError("o valor monetário possui mais de duas casas decimais")
    return amount.quantize(Decimal("0.01"))


def normalize_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = normalize_text(value)
    if text is None:
        raise NormalizationError("a data é obrigatória")
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    raise NormalizationError(f"formato de data não aceito: {text!r}")


def derived_source_record_id(fingerprint: DatasetFingerprint, row_number: int) -> str:
    if row_number < 1:
        raise NormalizationError("o número da linha deve ser igual ou maior que um")
    payload = f"{fingerprint.sha256}:{row_number}".encode()
    return f"row-{hashlib.sha256(payload).hexdigest()[:20]}"


def _row_value(row: Mapping[str, object], column: str | None) -> object | None:
    if column is None:
        return None
    if column not in row:
        raise NormalizationError(f"a coluna mapeada não foi encontrada: {column}")
    return row[column]


def normalize_row(
    row: Mapping[str, object],
    *,
    mapping: CanonicalMapping,
    dataset_id: str,
    side: DatasetSide,
    fingerprint: DatasetFingerprint,
    row_number: int,
) -> CanonicalTransaction:
    dataset = normalize_text(dataset_id)
    if dataset is None:
        raise NormalizationError("o identificador da fonte de dados é obrigatório")
    raw_source_id = normalize_identifier(_row_value(row, mapping.source_record_id))
    source_id = raw_source_id or derived_source_record_id(fingerprint, row_number)
    raw_transaction_id = normalize_identifier(_row_value(row, mapping.transaction_id))
    local_transaction_id = raw_transaction_id or source_id
    currency_value = normalize_identifier(_row_value(row, mapping.currency))
    currency = currency_value or mapping.default_currency.strip().upper()

    return CanonicalTransaction(
        transaction_id=f"{dataset}:{local_transaction_id}",
        dataset_id=dataset,
        side=side,
        money=Money(normalize_money(_row_value(row, mapping.amount)), currency),
        booking_date=normalize_date(_row_value(row, mapping.booking_date)),
        source_record_id=source_id,
        document=normalize_identifier(_row_value(row, mapping.document)),
        reference=normalize_identifier(_row_value(row, mapping.reference)),
    )
