.PHONY: install run dev test lint format typecheck security audit ci docker docker-canary clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

run:
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(VENV)/bin/pytest

lint:
	$(VENV)/bin/ruff check app tests
	$(VENV)/bin/ruff format --check app tests

format:
	$(VENV)/bin/ruff format app tests
	$(VENV)/bin/ruff check --fix app tests

typecheck:
	$(VENV)/bin/mypy app

security:
	$(VENV)/bin/bandit -q -c pyproject.toml -r app

audit:
	$(VENV)/bin/pip-audit --skip-editable

# Everything CI runs before a PR is allowed to merge. Run this before pushing.
ci: lint typecheck test security audit
	@echo "All local CI checks passed."

docker:
	docker build -t ai-production-pipeline:local .

docker-canary:
	docker compose -f docker-compose.yml up --build

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml .coverage
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
