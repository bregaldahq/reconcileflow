ifeq ($(OS),Windows_NT)
VENV_PY := .venv/Scripts/python.exe
NPM := npm.cmd
BACKEND_PY := set PYTHONPATH=backend/src&& $(VENV_PY) -P
BACKEND_TEST := cd backend&& set PYTHONPATH=src&& ..\.venv\Scripts\python.exe -m pytest tests
else
VENV_PY := .venv/bin/python
NPM := npm
BACKEND_PY := PYTHONPATH=backend/src $(VENV_PY) -P
BACKEND_TEST := cd backend && PYTHONPATH=src ../.venv/bin/python -m pytest tests
endif

.PHONY: setup verify verify-backend verify-frontend security demo test

setup:
	python -m venv .venv
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -e "./backend[dev]"
	$(NPM) --prefix frontend install

verify: verify-backend verify-frontend security

verify-backend:
	$(BACKEND_PY) scripts/check_repository.py
	$(BACKEND_PY) scripts/check_architecture.py
	$(BACKEND_PY) -m ruff format --check backend/src backend/tests backend/alembic scripts
	$(BACKEND_PY) -m ruff check backend/src backend/tests backend/alembic scripts
	$(BACKEND_PY) -m mypy --config-file backend/pyproject.toml backend/src
	$(BACKEND_TEST)
	$(BACKEND_PY) scripts/check_migrations.py

verify-frontend:
	$(NPM) --prefix frontend run verify

security:
	$(BACKEND_PY) -m bandit -c backend/pyproject.toml -r backend/src -q
	$(BACKEND_PY) scripts/check_secrets.py
	$(BACKEND_PY) -m pip_audit --local --skip-editable
	$(NPM) --prefix frontend audit --audit-level=high

test:
	$(BACKEND_TEST)

demo:
	docker compose up --build
