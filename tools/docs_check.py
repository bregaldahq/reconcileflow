from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    failures: list[str] = []

    required_cfg = json.loads((ROOT / "config" / "required_docs.json").read_text(encoding="utf-8"))
    for rel in required_cfg["required"]:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing required document: {rel}")
        elif path.stat().st_size == 0:
            failures.append(f"empty required document: {rel}")

    rules_cfg = json.loads((ROOT / "config" / "matching_rules.json").read_text(encoding="utf-8"))
    seen: set[tuple[str, int]] = set()

    for rule in rules_cfg["rules"]:
        key = (rule["id"], int(rule["version"]))
        if key in seen:
            failures.append(f"duplicate rule id/version: {key}")
        seen.add(key)

        doc = ROOT / rule["doc"]
        if not doc.exists():
            failures.append(f"rule {key} points to missing doc: {rule['doc']}")

    if failures:
        print("DOC CHECK FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("DOC CHECK PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
