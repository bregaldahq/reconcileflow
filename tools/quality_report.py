from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "generated" / "quality-report.json"

CHECKS = {
    "architecture": ["python", "tools/architecture_check.py"],
    "documentation": ["python", "tools/docs_check.py"],
    "specs": ["python", "tools/spec_check.py"],
    "fixtures": ["python", "tools/fixture_check.py"],
}

def run(cmd: list[str]) -> bool:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.returncode == 0

def main() -> int:
    results = {name: run(cmd) for name, cmd in CHECKS.items()}
    score = round((sum(results.values()) / len(results)) * 100)
    payload = {
        "score": score,
        "checks": results,
        "note": "Structural harness score. Implementation-stage tests/type/lint are enforced by scripts/verify.sh.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
