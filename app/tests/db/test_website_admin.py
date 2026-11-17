"""Website admin P1 tables (migration 0024; ADR 0012 auth, ADR 0014 system log).

- cp_website_admin: read/write the website_* admin tables; website_log is INSERT + SELECT only
  (no UPDATE, DELETE or TRUNCATE); no hard delete of website_user; no access to pilot_request,
  site_event or any web-app table.
- cp_website (public pages) and cp_app (web app) have no privilege on the admin tables.
- website_log_purge() deletes log rows older than 60 days and nothing newer.
- The last active admin cannot be demoted, disabled or deleted (pseudonymised).
- Checks: only IP prefixes (/24, /48), hash lengths, argon2id hashes, pseudonymised deletes.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import as_owner, as_role

pytestmark = pytest.mark.db

ADMIN = "cp_website_admin"
ADMIN_TABLES = (
    "website_user",
    "website_user_recovery_code",
    "website_session",
    "website_one_time_token",
    "website_rate_limit",
    "website_log",
    "website_job_run",
)
HASH = b"\x01" * 32
ARGON = "$argon2id$v=19$m=19456,t=2,p=1$c2FsdHNhbHQ$aGFzaGhhc2hoYXNoaGFzaA"


@pytest.fixture
def admin_db(db: psycopg.Connection) -> Iterator[psycopg.Connection]:
    with as_role(db, ADMIN):
        yield db


def add_user(conn: psycopg.Connection, email: str, role: str = "admin", **extra: Any) -> UUID:
    cols = ["email", "display_name", "role", *extra]
    vals = [email, email.split("@")[0], role, *extra.values()]
    marks = ", ".join(["%s"] * len(vals))
    row = conn.execute(
        f"insert into website_user ({', '.join(cols)}) values ({marks}) returning id", vals
    ).fetchone()
    assert row is not None
    return row[0]


def test_role_exists_without_login_or_bypass(db: psycopg.Connection) -> None:
    row = db.execute(
        "select rolcanlogin, rolbypassrls, rolsuper, rolcreaterole, rolcreatedb from pg_roles"
        " where rolname = %s",
        (ADMIN,),
    ).fetchone()
    assert row == (False, False, False, False, False)
    for other in ("cp_migrator", "cp_app", "cp_admin", "cp_website", "pg_read_all_data"):
        assert db.execute("select pg_has_role(%s, %s, 'member')", (ADMIN, other)).fetchone() == (
            False,
        ), other


def test_admin_role_touches_only_website_admin_tables(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select c.relname from pg_class c where c.relnamespace = 'public'::regnamespace"
        " and c.relkind in ('r', 'p', 'v')"
        " and (has_table_privilege(%s, c.oid, 'select')"
        "  or has_table_privilege(%s, c.oid, 'insert')"
        "  or has_table_privilege(%s, c.oid, 'update')"
        "  or has_table_privilege(%s, c.oid, 'delete'))",
        (ADMIN,) * 4,
    ).fetchall()
    # PostGIS catalog tables are readable by PUBLIC; nothing else outside the admin tables.
    postgis = {"geometry_columns", "geography_columns", "spatial_ref_sys"}
    assert {r[0] for r in rows} - postgis == set(ADMIN_TABLES)


@pytest.mark.parametrize("role", ["cp_website", "cp_app", "cp_admin"])
@pytest.mark.parametrize("table", ADMIN_TABLES)
def test_other_roles_have_no_access(db: psycopg.Connection, role: str, table: str) -> None:
    for priv in ("select", "insert", "update", "delete", "truncate"):
        row = db.execute("select has_table_privilege(%s, %s, %s)", (role, table, priv)).fetchone()
        assert row == (False,), (role, table, priv)


def test_log_is_append_only(admin_db: psycopg.Connection) -> None:
    admin_db.execute(
        "insert into website_log (kind, action, outcome) values ('auth', 'login', 'ok')"
    )
    for query in (
        "update website_log set action = 'x'",
        "delete from website_log",
        "truncate website_log",
    ):
        with pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
            admin_db.execute(query)


def test_log_update_refused_even_for_owner(db: psycopg.Connection) -> None:
    with as_owner(db):
        db.execute("insert into website_log (kind, action, outcome) values ('job', 'x', 'ok')")
        with pytest.raises(errors.InsufficientPrivilege), db.transaction():
            db.execute("update website_log set outcome = 'failed'")


def test_log_rejects_bad_values(admin_db: psycopg.Connection) -> None:
    bad = [
        ("auth", "Login With Spaces", "ok", None, "{}"),
        ("auth", "login", "ok", "203.0.113.7/32", "{}"),
        ("auth", "login", "ok", "2001:db8::1/128", "{}"),
        ("auth", "login", "ok", None, "[1, 2]"),
    ]
    for kind, action, outcome, ip, detail in bad:
        with pytest.raises(errors.CheckViolation), admin_db.transaction():
            admin_db.execute(
                "insert into website_log (kind, action, outcome, ip_prefix, detail)"
                " values (%s, %s, %s, %s, %s::jsonb)",
                (kind, action, outcome, ip, detail),
            )
    admin_db.execute(
        "insert into website_log (kind, action, outcome, ip_prefix) values"
        " ('auth', 'login', 'ok', '203.0.113.0/24'), ('auth', 'login', 'ok', '2001:db8:1::/48')"
    )


def test_purge_deletes_only_rows_older_than_60_days(admin_db: psycopg.Connection) -> None:
    with as_owner(admin_db):
        admin_db.execute(
            "insert into website_log (occurred_at, kind, action, outcome) values"
            " (now() - interval '60 days' - interval '1 second', 'auth', 'old', 'ok'),"
            " (now() - interval '59 days 23 hours', 'auth', 'recent', 'ok')"
        )
    removed = admin_db.execute("select website_log_purge()").fetchone()
    assert removed == (1,)
    actions = {r[0] for r in admin_db.execute("select action from website_log").fetchall()}
    assert "old" not in actions and "recent" in actions
    assert admin_db.execute("select website_log_purge()").fetchone() == (0,)


def test_purge_function_is_definer_pinned_and_not_public(db: psycopg.Connection) -> None:
    row = db.execute(
        "select p.prosecdef, p.proconfig, pg_get_userbyid(p.proowner),"
        " has_function_privilege('cp_website', p.oid, 'execute'),"
        " has_function_privilege('cp_app', p.oid, 'execute')"
        " from pg_proc p where p.proname = 'website_log_purge'"
    ).fetchone()
    assert row == (True, ['search_path=""'], "cp_migrator", False, False)


def test_purge_clears_expired_sessions_links_and_windows(admin_db: psycopg.Connection) -> None:
    user = add_user(admin_db, "a@example.com")
    with as_owner(admin_db):
        admin_db.execute(
            "insert into website_session (user_id, token_hash, csrf_token_hash, created_at,"
            " expires_at) values"
            " (%s, %s, %s, now() - interval '3 days', now() - interval '2 days'),"
            " (%s, %s, %s, now(), now() + interval '12 hours')",
            (user, b"\x02" * 32, HASH, user, b"\x03" * 32, HASH),
        )
        admin_db.execute(
            "insert into website_one_time_token (user_id, kind, token_hash, created_at, expires_at)"
            " values (%s, 'invite', %s, now() - interval '5 days', now() - interval '2 days')",
            (user, b"\x04" * 32),
        )
        admin_db.execute(
            "insert into website_rate_limit (key_hash, window_start, count) values"
            " (%s, now() - interval '2 days', 3), (%s, now(), 1)",
            (b"\x05" * 32, b"\x06" * 32),
        )
    admin_db.execute("select website_log_purge()")
    assert admin_db.execute("select count(*) from website_session").fetchone() == (1,)
    assert admin_db.execute("select count(*) from website_one_time_token").fetchone() == (0,)
    assert admin_db.execute("select count(*) from website_rate_limit").fetchone() == (1,)


def test_last_admin_cannot_be_removed(admin_db: psycopg.Connection) -> None:
    first = add_user(admin_db, "first@example.com")
    for query in (
        "update website_user set role = 'editor' where id = %s",
        "update website_user set disabled_at = now() where id = %s",
    ):
        with pytest.raises(errors.CheckViolation), admin_db.transaction():
            admin_db.execute(query, (first,))
    second = add_user(admin_db, "second@example.com")
    admin_db.execute("update website_user set disabled_at = now() where id = %s", (first,))
    with pytest.raises(errors.CheckViolation), admin_db.transaction():
        admin_db.execute("update website_user set role = 'author' where id = %s", (second,))


def test_users_are_never_hard_deleted(admin_db: psycopg.Connection) -> None:
    add_user(admin_db, "keep@example.com")
    editor = add_user(admin_db, "ed@example.com", role="editor")
    with pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
        admin_db.execute("delete from website_user where id = %s", (editor,))
    with as_owner(admin_db), pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
        admin_db.execute("delete from website_user where id = %s", (editor,))


def test_delete_means_pseudonymised(admin_db: psycopg.Connection) -> None:
    add_user(admin_db, "keep@example.com")
    editor = add_user(admin_db, "ed@example.com", role="editor", password_hash=ARGON)
    with pytest.raises(errors.CheckViolation), admin_db.transaction():
        admin_db.execute("update website_user set deleted_at = now() where id = %s", (editor,))
    admin_db.execute(
        "update website_user set deleted_at = now(), disabled_at = now(), email = null,"
        " password_hash = null where id = %s",
        (editor,),
    )


def test_user_checks(admin_db: psycopg.Connection) -> None:
    for kwargs in (
        {"password_hash": "$2b$10$bcrypt-is-not-allowed"},
        {"mfa_enabled_at": "2026-11-17"},
    ):
        with pytest.raises(errors.CheckViolation), admin_db.transaction():
            add_user(admin_db, "x@example.com", **kwargs)
    with pytest.raises(errors.CheckViolation), admin_db.transaction():
        add_user(admin_db, "Upper@Example.com")
    add_user(admin_db, "ok@example.com", password_hash=ARGON)
    with pytest.raises(errors.UniqueViolation), admin_db.transaction():
        add_user(admin_db, "ok@example.com")


def test_tokens_store_hashes_only_and_links_expire_within_72h(admin_db: psycopg.Connection) -> None:
    user = add_user(admin_db, "t@example.com")
    with pytest.raises(errors.CheckViolation), admin_db.transaction():
        admin_db.execute(
            "insert into website_session (user_id, token_hash, csrf_token_hash, expires_at)"
            " values (%s, %s, %s, now() + interval '1 hour')",
            (user, b"short", HASH),
        )
    with pytest.raises(errors.CheckViolation), admin_db.transaction():
        admin_db.execute(
            "insert into website_one_time_token (user_id, kind, token_hash, expires_at)"
            " values (%s, 'invite', %s, now() + interval '73 hours')",
            (user, HASH),
        )
    admin_db.execute(
        "insert into website_one_time_token (user_id, kind, token_hash, expires_at)"
        " values (%s, 'invite', %s, now() + interval '72 hours')",
        (user, HASH),
    )
