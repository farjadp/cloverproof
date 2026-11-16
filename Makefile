.PHONY: help setup hooks test lint fmt dev golden db-up db-down

help:
	@echo "make setup    install Python 3.12 and locked deps (uv)"
	@echo "make hooks    install pre-commit git hooks (see note in Makefile)"
	@echo "make lint     ruff lint + format check"
	@echo "make fmt      ruff format + autofix"
	@echo "make test     pytest (engine + app)"
	@echo "make dev      run the FastAPI app on http://127.0.0.1:8000"
	@echo "make golden   golden report (not available yet)"
	@echo "make db-up    start local Postgres + PostGIS (docker compose)"
	@echo "make db-down  stop local Postgres (data volume kept)"

setup:
	uv python install 3.12
	uv sync --locked

# Git hooks are shared by every worktree of this repo. Until .pre-commit-config.yaml
# is on every active branch, a hook installed here blocks commits on branches without it.
hooks:
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

dev:
	uv run uvicorn cloverproof_app.main:app --reload --host 127.0.0.1 --port 8000

golden:
	@echo "make golden: not available yet. The golden report arrives with engine v0 (web app plan, Step 3)."

db-up:
	docker compose up -d --wait db

db-down:
	docker compose down
