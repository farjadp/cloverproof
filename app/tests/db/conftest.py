"""Fixtures for database tests.

Opt-in: set TEST_DATABASE_URL to a superuser URL on a disposable Postgres + PostGIS
server (e.g. the `make db-up` container). There is deliberately no default, so tests
never touch a database by accident. Without it, or if the server is unreachable, every
test here is skipped and CI stays green (unless CP_DB_TESTS_REQUIRED=1, as in `make db-test`).

Each session creates a throwaway database `cp_test_<random>`, migrates it and drops it.
The cluster-wide roles (cp_migrator, cp_app, cp_admin, cp_website) are created on that
server if missing.

Tests run inside one transaction per test (rolled back), acting as `cp_app` unless they
switch with `as_owner` / `as_role`. `insert()` writes `organisation` and `membership` as the
superuser (operator setup): cp_app has no write grant there (ADR 0007).
"""

from __future__ import annotations

import copy
import os
import secrets
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from cloverproof_app.db.migrate import DEFAULT_MIGRATIONS_DIR, REPO_ROOT, migrate
from cloverproof_engine import recommend
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import Crop, RecommendationInput

PLACEHOLDER_PACK_PATH = REPO_ROOT / "packs" / "placeholder" / "v0.yaml"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "db: needs TEST_DATABASE_URL (skipped without it)")


@dataclass
class MigratedDb:
    url: str
    first_run: list[str]


def _unavailable(reason: str) -> None:
    # `make db-test` sets CP_DB_TESTS_REQUIRED=1: a missing database is then a failure.
    if os.environ.get("CP_DB_TESTS_REQUIRED") == "1":
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="session")
def admin_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        _unavailable("TEST_DATABASE_URL not set (database tests are opt-in)")
    try:
        with psycopg.connect(url, connect_timeout=3):
            pass
    except psycopg.OperationalError as error:
        _unavailable(f"test database not reachable: {error.__class__.__name__}")
    return url


@pytest.fixture(scope="session")
def migrated_db(admin_url: str) -> Iterator[MigratedDb]:
    name = f"cp_test_{secrets.token_hex(4)}"
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(f'create database "{name}"')
    url = make_conninfo(admin_url, dbname=name)
    try:
        with psycopg.connect(url, autocommit=True) as conn:
            first_run = migrate(conn, DEFAULT_MIGRATIONS_DIR, log=lambda _: None)
        yield MigratedDb(url=url, first_run=first_run)
    finally:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(f'drop database if exists "{name}" with (force)')


@pytest.fixture
def db(migrated_db: MigratedDb) -> Iterator[psycopg.Connection]:
    with psycopg.connect(migrated_db.url) as conn:
        conn.execute("set local role cp_app")
        try:
            yield conn
        finally:
            conn.rollback()


@contextmanager
def as_role(conn: psycopg.Connection, role: str | None) -> Iterator[None]:
    """Run the block as `role` (None = the connecting superuser), inside a savepoint.

    Afterwards the previous role is restored; on error the savepoint rollback restores it.
    """
    row = conn.execute("select current_user").fetchone()
    assert row is not None
    with conn.transaction():
        if role is None:
            conn.execute("reset role")
        else:
            conn.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
        yield
        conn.execute(sql.SQL("set local role {}").format(sql.Identifier(row[0])))


def as_owner(conn: psycopg.Connection) -> AbstractContextManager[None]:
    """Run the block as the connecting superuser instead of cp_app, inside a savepoint."""
    return as_role(conn, None)


# Identity tables only an operator (cp_admin / superuser) may write (migration 0011).
OPERATOR_TABLES = frozenset({"organisation", "membership"})


def insert(conn: psycopg.Connection, table: str, **values: Any) -> UUID:
    cols = ", ".join(values)
    marks = ", ".join(["%s"] * len(values))
    params = [Jsonb(v) if isinstance(v, dict) else v for v in values.values()]
    query = f"insert into {table} ({cols}) values ({marks}) returning id"
    with as_owner(conn) if table in OPERATOR_TABLES else nullcontext():
        row = conn.execute(query, params).fetchone()  # type: ignore[arg-type]
    assert row is not None
    return row[0]


@pytest.fixture(scope="session")
def engine_result() -> dict[str, Any]:
    """A real engine output (placeholder pack, no soil test), as stored in `result`."""
    pack = load_pack(PLACEHOLDER_PACK_PATH)
    inputs = RecommendationInput(
        crop=Crop.WHEAT,
        target_yield_t_ha=5.0,
        previous_crop="wheat",
        area_ha=10.0,
        plan_date=date(2027, 2, 1),
    )
    return recommend(inputs, pack).model_dump(mode="json")


def recommendation_values(result: dict[str, Any]) -> dict[str, Any]:
    """Typed columns copied from an engine document."""
    return {
        "inputs_snapshot": result["input_snapshot"],
        "result": result,
        "engine_version": result["engine_version"],
        "pack_id": result["pack_id"],
        "pack_version": result["pack_version"],
        "pack_status": result["pack_status"],
        "pack_sha256": result["pack_sha256"],
        "confidence": result["confidence"],
    }


def edited(result: dict[str, Any], n_rate: float) -> dict[str, Any]:
    """The agronomist's version: same document, final N rate replaced."""
    doc = copy.deepcopy(result)
    doc["nitrogen"]["rate"]["value"] = n_rate
    return doc


@dataclass
class Org:
    id: UUID
    agronomist: UUID
    staff: UUID
    farmer: UUID
    farm: UUID
    fields: list[UUID]
    season: UUID
    crop_plan: UUID
    engine_rec: UUID


def make_org(conn: psycopg.Connection, label: str, result: dict[str, Any]) -> Org:
    org = insert(conn, "organisation", name=f"Test org {label}")
    agronomist = insert(
        conn, "app_user", email=f"agro-{label}@example.org", display_name=f"Agro {label}"
    )
    staff = insert(
        conn, "app_user", email=f"staff-{label}@example.org", display_name=f"Staff {label}"
    )
    insert(conn, "membership", organisation_id=org, user_id=agronomist, role="agronomist")
    insert(conn, "membership", organisation_id=org, user_id=staff, role="staff")
    farmer = insert(conn, "farmer", organisation_id=org, display_name=f"Farmer {label}")
    farm = insert(conn, "farm", organisation_id=org, farmer_id=farmer, name=f"Farm {label}")
    fields = [
        insert(conn, "field", organisation_id=org, farm_id=farm, name=f"Field {label}{i}")
        for i in (1, 2)
    ]
    season = insert(conn, "season", organisation_id=org, label="2027")
    crop_plan = insert(
        conn,
        "crop_plan",
        organisation_id=org,
        field_id=fields[0],
        season_id=season,
        crop="wheat",
        target_yield_t_ha=5.0,
        previous_crop="wheat",
        plan_date=date(2027, 2, 1),
        created_by=staff,
    )
    engine_rec = insert(
        conn,
        "recommendation",
        organisation_id=org,
        crop_plan_id=crop_plan,
        kind="engine",
        created_by=staff,
        **recommendation_values(result),
    )
    return Org(org, agronomist, staff, farmer, farm, fields, season, crop_plan, engine_rec)


@pytest.fixture
def org_a(db: psycopg.Connection, engine_result: dict[str, Any]) -> Org:
    return make_org(db, "a", engine_result)


@pytest.fixture
def org_b(db: psycopg.Connection, engine_result: dict[str, Any]) -> Org:
    return make_org(db, "b", engine_result)
