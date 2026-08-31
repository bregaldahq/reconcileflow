"""Fail on forbidden outward dependencies in inward layers."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend" / "src" / "reconcileflow"
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "domain": (
        "alembic",
        "celery",
        "fastapi",
        "httpx",
        "openpyxl",
        "pandas",
        "polars",
        "psycopg",
        "redis",
        "reconcileflow.adapters",
        "reconcileflow.api",
        "reconcileflow.application",
        "sqlalchemy",
    ),
    "application": (
        "alembic",
        "celery",
        "fastapi",
        "openpyxl",
        "pandas",
        "polars",
        "psycopg",
        "redis",
        "reconcileflow.adapters",
        "reconcileflow.api",
        "sqlalchemy",
    ),
}


def imported_modules(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
    return imports


def main() -> int:
    violations: list[str] = []
    checked = 0
    for layer, blocked in FORBIDDEN.items():
        directory = SOURCE / layer
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.py")):
            checked += 1
            for line, module in imported_modules(path):
                if any(module == prefix or module.startswith(f"{prefix}.") for prefix in blocked):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{line} imports forbidden module {module!r}"
                    )
    if violations:
        print("Architecture boundary check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print(f"Architecture boundaries passed ({checked} inward-layer modules checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
