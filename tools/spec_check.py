from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"

REQUIRED_HEADINGS = (
    "## Goal",
    "## Acceptance criteria",
    "## Architecture constraints",
    "## Verification",
)

TASK_RE = re.compile(r"^# (RF-\d{3})\s+—\s+.+$", re.MULTILINE)

def main() -> int:
    failures: list[str] = []

    for path in sorted(SPECS.glob("RF-*.md")):
        text = path.read_text(encoding="utf-8")
        if not TASK_RE.search(text):
            failures.append(f"{path.name}: invalid/missing RF task heading")
        for heading in REQUIRED_HEADINGS:
            if heading not in text:
                failures.append(f"{path.name}: missing heading '{heading}'")

    if failures:
        print("SPEC CHECK FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("SPEC CHECK PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
