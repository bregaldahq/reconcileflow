#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
echo "Virtualenv created at .venv"
echo "Activate it and install:"
echo "  python -m pip install -e '.[dev]'"
echo
echo "Then run:"
echo "  make verify"
