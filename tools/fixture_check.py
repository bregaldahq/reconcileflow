from __future__ import annotations

import csv
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "fixtures" / "golden" / "manifest.json"

def validate_money_csv(path: Path) -> list[str]:
    failures: list[str] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if "amount" not in (reader.fieldnames or []):
            failures.append(f"{path}: missing amount column")
            return failures
        for row_no, row in enumerate(reader, start=2):
            try:
                Decimal(row["amount"])
            except (InvalidOperation, KeyError):
                failures.append(f"{path}:{row_no}: invalid canonical decimal amount")
    return failures

def main() -> int:
    failures: list[str] = []
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for fixture in data["fixtures"]:
        folder = ROOT / fixture["path"]
        for required in ("source.csv", "target.csv", "expected.json"):
            path = folder / required
            if not path.exists():
                failures.append(f"{fixture['id']}: missing {required}")
        for csv_name in ("source.csv", "target.csv"):
            path = folder / csv_name
            if path.exists():
                failures.extend(validate_money_csv(path))

        expected = folder / "expected.json"
        if expected.exists():
            payload = json.loads(expected.read_text(encoding="utf-8"))
            if payload.get("fixture_id") != fixture["id"]:
                failures.append(f"{fixture['id']}: expected.json fixture_id mismatch")

    if failures:
        print("FIXTURE CHECK FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("FIXTURE CHECK PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
