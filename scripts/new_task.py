from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "specs" / "000-template.md"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def main() -> int:
    if len(sys.argv) != 3:
        print('Usage: python scripts/new_task.py RF-004 "Exact matching"')
        return 2

    task_id, title = sys.argv[1], sys.argv[2]
    if not re.fullmatch(r"RF-\d{3}", task_id):
        print("Task ID must match RF-000")
        return 2

    destination = ROOT / "specs" / f"{task_id}-{slugify(title)}.md"
    if destination.exists():
        print(f"Refusing to overwrite {destination.relative_to(ROOT)}")
        return 1

    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("# TASK-ID — Short title", f"# {task_id} — {title}")
    destination.write_text(text, encoding="utf-8")
    print(destination.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
