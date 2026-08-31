from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOMAIN = ROOT / "reconcileflow" / "domain"

FORBIDDEN_DOMAIN_PREFIXES = (
    "fastapi",
    "sqlalchemy",
    "pandas",
    "polars",
    "celery",
    "redis",
    "requests",
    "httpx",
    "reconcileflow.infrastructure",
    "apps",
)

def imported_modules(path: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        print(f"[architecture] syntax error in {path}: {exc}")
        raise

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.lineno, node.module))
    return found

def main() -> int:
    failures: list[str] = []

    if DOMAIN.exists():
        for path in DOMAIN.rglob("*.py"):
            for lineno, module in imported_modules(path):
                if module.startswith(FORBIDDEN_DOMAIN_PREFIXES):
                    rel = path.relative_to(ROOT)
                    failures.append(f"{rel}:{lineno} imports forbidden module '{module}'")

    if failures:
        print("ARCHITECTURE CHECK FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("ARCHITECTURE CHECK PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
