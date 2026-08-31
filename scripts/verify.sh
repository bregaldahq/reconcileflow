#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STAGE="${HARNESS_STAGE:-$(tr -d '[:space:]' < .harness-stage)}"

echo "== ReconcileFlow quality gate =="
echo "stage: $STAGE"
echo

python tools/docs_check.py
python tools/spec_check.py
python tools/fixture_check.py
python tools/architecture_check.py

if [[ "$STAGE" == "implementation" ]]; then
  echo
  echo "== implementation checks =="

  for cmd in ruff mypy pytest; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "MISSING REQUIRED TOOL: $cmd"
      echo "Install development dependencies before using implementation stage."
      exit 1
    fi
  done

  ruff check .
  ruff format --check .
  mypy reconcileflow

  pytest \
    --cov=reconcileflow \
    --cov-branch \
    --cov-report=term-missing \
    --cov-fail-under=80
fi

echo
echo "QUALITY GATE PASSED"
