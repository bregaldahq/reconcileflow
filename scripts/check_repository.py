"""Validate required sources of truth and synthetic fixture references."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "AGENTS.md",
    "ARCHITECTURE.md",
    "docs/PRODUCT.md",
    "docs/DOMAIN.md",
    "docs/RELIABILITY.md",
    "docs/SECURITY.md",
    "docs/QUALITY.md",
    "docs/product-specs/reconciliation-workflow.md",
    "docs/product-specs/matching-rules.md",
    "docs/product-specs/ingestion-and-export.md",
    "docs/product-specs/analyst-guidance-and-visualizations.md",
    "specs/RF-001-domain-foundation.md",
    "specs/RF-002-normalization.md",
    "specs/RF-003-exact-matching.md",
    "specs/RF-004-tolerance-matching.md",
    "specs/RF-005-split-matching.md",
    "specs/RF-006-platform-slices.md",
    "specs/RF-007-guided-analyst-experience.md",
    "specs/RF-008-ci-cd.md",
    "fixtures/manifest.json",
    "fixtures/demo/ledger-a.csv",
    "fixtures/demo/settlement-b.csv",
    "README.md",
    "compose.yaml",
    "compose.production.yaml",
    "backend/Dockerfile",
    "frontend/Dockerfile",
    ".env.example",
    ".env.production.example",
    ".github/dependabot.yml",
    ".github/workflows/ci-cd.yml",
    "docs/DEPLOYMENT.md",
    "scripts/deploy_remote.sh",
    "scripts/smoke_test.sh",
    "evals/architecture-pressure.md",
    "evals/happy-path-pressure.md",
    "evals/nondeterministic-candidates.md",
    "evals/test-weakening.md",
    "evals/async-delivery-pressure.md",
    "evals/generic-ai-dashboard-pressure.md",
)


def main() -> int:
    problems: list[str] = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            problems.append(f"missing or empty required file: {relative}")

    adrs = sorted((ROOT / "docs" / "adr").glob("*.md"))
    if not adrs:
        problems.append("at least one ADR is required")
    for adr in adrs:
        text = adr.read_text(encoding="utf-8")
        has_inline_status = "Status: " in text
        has_section_status = re.search(r"^## Status\s*$\n+\s*\S+", text, flags=re.MULTILINE)
        if not has_inline_status and has_section_status is None:
            problems.append(f"ADR has no status: {adr.relative_to(ROOT)}")

    manifest_path = ROOT / "fixtures" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        problems.append(f"fixture manifest is invalid: {error}")
    else:
        if manifest.get("synthetic_only") is not True:
            problems.append("fixture manifest must declare synthetic_only=true")
        scenario_ids: set[str] = set()
        for scenario in manifest.get("scenarios", []):
            scenario_id = scenario.get("id")
            if not scenario_id or scenario_id in scenario_ids:
                problems.append(f"fixture scenario ID is empty or repeated: {scenario_id!r}")
            scenario_ids.add(scenario_id)
            relative_path = scenario.get("path", "")
            if not relative_path or not (ROOT / relative_path).is_file():
                problems.append(f"fixture scenario path does not exist: {relative_path!r}")

    if problems:
        print("Repository consistency failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"Repository consistency passed ({len(REQUIRED)} required files, {len(adrs)} ADRs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
