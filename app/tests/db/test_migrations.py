"""Migrations apply from empty, re-run is a no-op, and the shape matches the website runner."""

import psycopg
import pytest

from cloverproof_app.db.migrate import DEFAULT_MIGRATIONS_DIR, migrate, migration_files
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.models import (
    ConcentrationUnit,
    ExtractionMethod,
    NutrientForm,
    SoilTestSource,
)

from .conftest import MigratedDb, as_owner

pytestmark = pytest.mark.db


def test_apply_from_empty_runs_every_file(migrated_db: MigratedDb) -> None:
    assert migrated_db.first_run == [p.name for p in migration_files(DEFAULT_MIGRATIONS_DIR)]


def test_rerun_is_noop(migrated_db: MigratedDb) -> None:
    lines: list[str] = []
    with psycopg.connect(migrated_db.url, autocommit=True) as conn:
        assert migrate(conn, DEFAULT_MIGRATIONS_DIR, log=lines.append) == []
        count = conn.execute("select count(*) from schema_migrations").fetchone()
    assert lines == ["migrate: up to date"]
    assert count == (len(migrated_db.first_run),)


def test_schema_migrations_shape_matches_website_runner(db: psycopg.Connection) -> None:
    # website/scripts/migrate.mjs: (name text primary key, applied_at timestamptz not null
    # default now()), keyed by file name.
    with as_owner(db):
        cols = db.execute(
            """select column_name, data_type, is_nullable, column_default
               from information_schema.columns
               where table_name = 'schema_migrations' order by ordinal_position"""
        ).fetchall()
        pk = db.execute(
            """select a.attname from pg_index i
               join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey)
               where i.indrelid = 'schema_migrations'::regclass and i.indisprimary"""
        ).fetchall()
        names = db.execute("select name from schema_migrations order by name").fetchall()
    assert cols == [
        ("name", "text", "NO", None),
        ("applied_at", "timestamp with time zone", "NO", "now()"),
    ]
    assert pk == [("name",)]
    assert names[0] == ("0001_pilot_request.sql",)


def test_app_objects_owned_by_cp_migrator(db: psycopg.Connection) -> None:
    rows = db.execute(
        """select tablename, tableowner from pg_tables
           where schemaname = 'public'
             and tablename not in ('schema_migrations', 'pilot_request', 'spatial_ref_sys')"""
    ).fetchall()
    assert rows
    assert {owner for _, owner in rows} == {"cp_migrator"}


def test_roles_have_no_login(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select rolname, rolcanlogin from pg_roles"
        " where rolname in ('cp_migrator', 'cp_app') order by 1"
    ).fetchall()
    assert rows == [("cp_app", False), ("cp_migrator", False)]


@pytest.mark.parametrize(
    ("pg_type", "engine_enum"),
    [
        ("soil_test_source", SoilTestSource),
        ("nutrient_form", NutrientForm),
        ("concentration_unit", ConcentrationUnit),
        ("extraction_method", ExtractionMethod),
    ],
)
def test_enums_match_engine(db: psycopg.Connection, pg_type: str, engine_enum: type) -> None:
    labels = db.execute(
        "select unnest(enum_range(null::" + pg_type + "))::text"  # type: ignore[operator]
    ).fetchall()
    assert {label for (label,) in labels} == {member.value for member in engine_enum}


def test_confidence_enum_matches_engine(db: psycopg.Connection) -> None:
    labels = db.execute("select unnest(enum_range(null::confidence_level))::text").fetchall()
    assert {label for (label,) in labels} == {c.value for c in Confidence}
