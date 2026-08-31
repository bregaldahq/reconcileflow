from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

from reconcileflow.adapters.ingestion import IngestionLimits, TabularDatasetParser
from reconcileflow.application.errors import DatasetValidationError


def xlsx_bytes(rows: tuple[tuple[object, ...], ...]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def test_csv_parser_detects_semicolon_and_fingerprints_original_bytes() -> None:
    content = b"id;amount\n1;1.234,56\n"
    parsed = TabularDatasetParser().parse(
        filename="data.csv", content_type="text/csv", content=content
    )
    assert parsed.headers == ("id", "amount")
    assert parsed.rows[0]["amount"] == "1.234,56"
    assert parsed.fingerprint == parsed.fingerprint.from_bytes(content)


def test_xlsx_parser_converts_float_before_domain_boundary() -> None:
    parsed = TabularDatasetParser().parse(
        filename="data.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=xlsx_bytes((("id", "amount"), ("1", 12.5))),
    )
    assert parsed.rows[0]["amount"] == "12.5"
    assert not isinstance(parsed.rows[0]["amount"], float)


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "code"),
    [
        ("data.txt", "text/plain", b"x", "unsupported_file_type"),
        ("data.csv", "application/json", b"x", "invalid_content_type"),
        ("data.xlsx", "application/octet-stream", b"not-zip", "invalid_signature"),
        ("data.csv", "text/csv", b"a,a\n1,2\n", "duplicate_header"),
    ],
)
def test_parser_rejects_invalid_uploads(
    filename: str, content_type: str, content: bytes, code: str
) -> None:
    with pytest.raises(DatasetValidationError) as captured:
        TabularDatasetParser().parse(filename=filename, content_type=content_type, content=content)
    assert captured.value.issues[0].code == code


def test_upload_and_cell_limits_are_explicit() -> None:
    parser = TabularDatasetParser(IngestionLimits(max_bytes=5, max_cell_characters=3))
    with pytest.raises(DatasetValidationError, match="validação da fonte de dados falhou"):
        parser.parse(filename="data.csv", content_type="text/csv", content=b"123456")
    cell_parser = TabularDatasetParser(IngestionLimits(max_bytes=100, max_cell_characters=3))
    with pytest.raises(DatasetValidationError) as captured:
        cell_parser.parse(filename="data.csv", content_type="text/csv", content=b"a\nlong\n")
    assert captured.value.issues[0].code == "cell_too_large"
