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

Row-level security (ADR 0008, migration 0021): cp_app sees tenant rows only with a context.
`insert()` into a tenant table runs as cp_app with a temporary context (the row's
organisation and its author, or another enabled member of that organisation) and restores
the previous context afterwards, so fixtures exercise the policies. Tests that read or
write tenant tables directly call `use_context(conn, user, org)` first. The `org_a` fixture
leaves org A's agronomist in org A as the default context. Requests through the app set the
context in auth.py like production.
"""

from __future__ import annotations

import copy
import os
import secrets
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
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
# Tenant tables (RLS, migration 0021) whose organisation column is not `organisation_id`.
ORG_COLUMN = {"access_grant": "owner_organisation_id"}
# Columns the insert policies bind to the context user (ADR 0008 §4.4).
AUTHOR_COLUMNS = ("created_by", "reviewer_id", "granted_by")
CONTEXT_KEYS = ("app.user_id", "app.org_id", "app.platform_role")


def use_context(
    conn: psycopg.Connection,
    user_id: UUID | None,
    org_id: UUID | None = None,
    platform_role: str | None = None,
) -> None:
    """Set the RLS context for the rest of the test transaction (like auth.py does)."""
    conn.execute(
        "select set_config('app.user_id', %s, true), set_config('app.org_id', %s, true),"
        " set_config('app.platform_role', %s, true)",
        (str(user_id) if user_id else "", str(org_id) if org_id else "", platform_role or ""),
    )


def current_context(conn: psycopg.Connection) -> tuple[str, str, str]:
    row = conn.execute(
        "select coalesce(current_setting(%s, true), ''), coalesce(current_setting(%s, true), ''),"
        " coalesce(current_setting(%s, true), '')",
        CONTEXT_KEYS,
    ).fetchone()
    assert row is not None
    return row


def restore_context(conn: psycopg.Connection, saved: tuple[str, str, str]) -> None:
    conn.execute(
        "select set_config(%s, %s, true), set_config(%s, %s, true), set_config(%s, %s, true)",
        [x for pair in zip(CONTEXT_KEYS, saved, strict=True) for x in pair],
    )


def member_of(conn: psycopg.Connection, org_id: UUID) -> UUID | None:
    """An enabled member of the organisation (humans first), to act as in fixtures."""
    row = conn.execute(
        "select m.user_id from membership m join app_user u on u.id = m.user_id"
        " where m.organisation_id = %s and u.disabled_at is null"
        " order by (u.actor_kind = 'human') desc, m.created_at, m.user_id limit 1",
        (org_id,),
    ).fetchone()
    return row[0] if row else None


@contextmanager
def tenant_context(conn: psycopg.Connection, table: str, values: dict[str, Any]) -> Iterator[None]:
    """Temporary context for one fixture insert into a tenant table; restored afterwards."""
    org_id = values.get(ORG_COLUMN.get(table, "organisation_id"))
    if org_id is None:
        yield
        return
    user_id = next((values[c] for c in AUTHOR_COLUMNS if values.get(c)), None)
    saved = current_context(conn)
    use_context(conn, user_id or member_of(conn, org_id), org_id)
    yield
    restore_context(conn, saved)


def insert(conn: psycopg.Connection, table: str, **values: Any) -> UUID:
    cols = ", ".join(values)
    marks = ", ".join(["%s"] * len(values))
    params = [Jsonb(v) if isinstance(v, dict) else v for v in values.values()]
    query = f"insert into {table} ({cols}) values ({marks}) returning id"
    context = as_owner(conn) if table in OPERATOR_TABLES else tenant_context(conn, table, values)
    with conn.transaction(), context:
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
    insert(conn, "membership", organisation_id=org, user_id=staff, role="advisor")
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
    """Org A. Default RLS context of a test that uses it: org A's agronomist in org A."""
    org = make_org(db, "a", engine_result)
    use_context(db, org.agronomist, org.id)
    return org


@pytest.fixture
def org_b(db: psycopg.Connection, engine_result: dict[str, Any]) -> Org:
    return make_org(db, "b", engine_result)
