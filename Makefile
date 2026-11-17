.PHONY: help setup hooks test lint fmt dev golden db-up db-down db-migrate db-seed db-test user-create

help:
	@echo "make setup    install Python 3.12 and locked deps (uv)"
	@echo "make hooks    install pre-commit git hooks (see note in Makefile)"
	@echo "make lint     ruff lint + format check"
	@echo "make fmt      ruff format + autofix"
	@echo "make test     pytest (engine + app)"
	@echo "make dev      run the FastAPI app on http://127.0.0.1:8000"
	@echo "make golden   golden report (engine vs expected, report only)"
	@echo "make db-up    start local Postgres + PostGIS (docker compose)"
	@echo "make db-down  stop local Postgres (data volume kept)"
	@echo "make db-migrate  apply db/migrations to DATABASE_URL"
	@echo "make db-seed     load db/seeds/dev.sql into DATABASE_URL (local hosts only)"
	@echo "make db-test     DB tests against TEST_DATABASE_URL (superuser, disposable server)"
	@echo "make user-create EMAIL=... ORG=... ROLE=agronomist [ARGS=--create-org]  (asks for the password)"

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
	uv run uvicorn cloverproof_app.main:create_app --factory --reload --host 127.0.0.1 --port 8000

golden:
	uv run python -m cloverproof_engine.golden_report --golden-dir engine/tests/golden --packs-dir packs

db-up:
	docker compose up -d --wait db

db-down:
	docker compose down

# No default URLs on purpose: a wrong default can hit another local Postgres on 5432.
# Local example: postgresql://postgres:postgres@127.0.0.1:5432/cloverproof
db-migrate:
	uv run python -m cloverproof_app.db.migrate up

db-seed:
	uv run python -m cloverproof_app.db.migrate seed db/seeds/dev.sql

db-test:
	@test -n "$$TEST_DATABASE_URL" || { echo "TEST_DATABASE_URL is not set"; exit 1; }
	CP_DB_TESTS_REQUIRED=1 uv run pytest app/tests/db -rs

# Password is asked interactively (getpass); it is never a make variable or argv.
user-create:
	@test -n "$(EMAIL)" -a -n "$(ORG)" -a -n "$(ROLE)" || { echo "usage: make user-create EMAIL=... ORG=... ROLE=org_admin|agronomist|advisor [ARGS='--create-org --name ...']"; exit 1; }
	uv run python -m cloverproof_app.cli user-create --email "$(EMAIL)" --org "$(ORG)" --role "$(ROLE)" $(ARGS)
