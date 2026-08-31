$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    throw "Run 'make setup' (or create .venv and install backend[dev]) before verification."
}

& ".venv\Scripts\python.exe" "scripts\check_repository.py"
& ".venv\Scripts\python.exe" "scripts\check_architecture.py"
& ".venv\Scripts\python.exe" -m ruff format --check backend/src backend/tests backend/alembic scripts
& ".venv\Scripts\python.exe" -m ruff check backend/src backend/tests backend/alembic scripts
& ".venv\Scripts\python.exe" -m mypy --config-file backend/pyproject.toml backend/src
& ".venv\Scripts\python.exe" -m pytest backend/tests
& ".venv\Scripts\python.exe" "scripts\check_migrations.py"
& npm.cmd --prefix frontend run verify
& ".venv\Scripts\python.exe" -m bandit -c backend/pyproject.toml -r backend/src -q
& ".venv\Scripts\python.exe" "scripts\check_secrets.py"
& ".venv\Scripts\python.exe" -m pip_audit --local --skip-editable
& npm.cmd --prefix frontend audit --audit-level=high
