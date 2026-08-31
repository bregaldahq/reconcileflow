"""Validate that Alembic metadata is at a single head when persistence exists."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALEMBIC = ROOT / "backend" / "alembic.ini"


def main() -> int:
    if not ALEMBIC.exists():
        print("Migration validation pending: persistence slice not present.")
        return 0
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC), "heads"],
        cwd=ROOT / "backend",
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        print(result.stdout)
        print(result.stderr)
        return result.returncode
    heads = [line for line in result.stdout.splitlines() if "(head)" in line]
    if len(heads) != 1:
        print(f"Expected one Alembic head, found {len(heads)}: {heads}")
        return 1
    print(f"Migration validation passed: {heads[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
