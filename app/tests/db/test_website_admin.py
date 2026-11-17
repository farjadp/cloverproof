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

import threading
import time
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import MigratedDb, as_owner, as_role

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
    "website_secret",
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
    # Deleted stays deleted: no undelete, no renaming.
    for query in (
        "update website_user set deleted_at = null where id = %s",
        "update website_user set display_name = 'back' where id = %s",
    ):
        with pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
            admin_db.execute(query, (editor,))


def test_history_columns_cannot_be_rewritten(admin_db: psycopg.Connection) -> None:
    user = add_user(admin_db, "h@example.com")
    for column, value in (
        ("id", "00000000-0000-0000-0000-000000000001"),
        ("created_at", "1900-01-01"),
        ("created_by", None),
    ):
        with pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
            admin_db.execute(f"update website_user set {column} = %s where id = %s", (value, user))


def test_recovery_codes_can_be_removed(admin_db: psycopg.Connection) -> None:
    user = add_user(admin_db, "r@example.com")
    admin_db.execute(
        "insert into website_user_recovery_code (user_id, code_hash) values (%s, %s)", (user, HASH)
    )
    admin_db.execute("delete from website_user_recovery_code where user_id = %s", (user,))


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


@pytest.mark.parametrize("isolation", ["read committed", "repeatable read", "serializable"])
def test_last_admin_guard_holds_under_concurrency(migrated_db: MigratedDb, isolation: str) -> None:
    """Two admins disabled at the same time from two connections: one must fail."""
    with psycopg.connect(migrated_db.url, autocommit=True) as setup:
        ids = [
            setup.execute(
                "insert into website_user (email, display_name, role) values (%s, 'race', 'admin')"
                " returning id",
                (f"race-{isolation.replace(' ', '-')}-{n}@example.com",),
            ).fetchone()[0]  # type: ignore[index]
            for n in (1, 2)
        ]
    errors_seen: list[BaseException] = []
    try:
        with (
            psycopg.connect(migrated_db.url) as first,
            psycopg.connect(migrated_db.url) as second,
        ):
            for conn in (first, second):
                conn.execute(f"set transaction isolation level {isolation}")
                conn.execute("set local role cp_website_admin")
            # Both transactions take their snapshot before either change commits.
            first.execute("select count(*) from website_user").fetchone()
            second.execute("select count(*) from website_user").fetchone()
            first.execute("update website_user set disabled_at = now() where id = %s", (ids[0],))

            def disable_second() -> None:
                try:
                    second.execute(
                        "update website_user set disabled_at = now() where id = %s", (ids[1],)
                    )
                    second.commit()
                except psycopg.Error as error:
                    errors_seen.append(error)
                    second.rollback()

            worker = threading.Thread(target=disable_second)
            worker.start()
            time.sleep(0.5)  # second is now waiting on the advisory lock
            first.commit()
            worker.join(timeout=10)
        assert len(errors_seen) == 1
        assert isinstance(errors_seen[0], (errors.CheckViolation, errors.SerializationFailure)), (
            errors_seen[0]
        )
        with psycopg.connect(migrated_db.url) as check:
            active = check.execute(
                "select count(*) from website_user where id = any(%s) and disabled_at is null",
                (ids,),
            ).fetchone()
        assert active == (1,)
    finally:
        with psycopg.connect(migrated_db.url, autocommit=True) as cleanup:
            # Superuser cleanup only: users are never deleted by any app role.
            cleanup.execute("set session_replication_role = replica")
            cleanup.execute("delete from website_user where id = any(%s)", (ids,))


# --- website_secret (migration 0025, ADR 0013)

SEALED = b'{"v":1,' + b"x" * 80 + b"}"


def add_secret(
    conn: psycopg.Connection, user: UUID, provider: str = "anthropic", version: int = 1
) -> UUID:
    row = conn.execute(
        "insert into website_secret (provider, version, sealed, kek_id, last4, created_by)"
        " values (%s, %s, %s, 'k1', 'AbC9', %s) returning id",
        (provider, version, SEALED, user),
    ).fetchone()
    assert row is not None
    return row[0]


def test_one_active_key_per_provider(admin_db: psycopg.Connection) -> None:
    user = add_user(admin_db, "k@example.com")
    first = add_secret(admin_db, user)
    with pytest.raises(errors.UniqueViolation), admin_db.transaction():
        add_secret(admin_db, user, version=2)
    admin_db.execute(
        "update website_secret set revoked_at = now(), revoked_by = %s where id = %s", (user, first)
    )
    add_secret(admin_db, user, version=2)
    add_secret(admin_db, user, provider="openai")


def test_secret_rows_are_immutable_and_never_deleted(admin_db: psycopg.Connection) -> None:
    user = add_user(admin_db, "k@example.com")
    key = add_secret(admin_db, user)
    with pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
        admin_db.execute(
            "update website_secret set sealed = %s where id = %s", (SEALED + b" ", key)
        )
    with pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
        admin_db.execute("delete from website_secret where id = %s", (key,))
    with as_owner(admin_db), pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
        admin_db.execute("update website_secret set last4 = 'zzzz' where id = %s", (key,))
    admin_db.execute(
        "update website_secret set monthly_budget_usd = 25, last_test_at = now(),"
        " last_test_ok = true where id = %s",
        (key,),
    )
    admin_db.execute(
        "update website_secret set revoked_at = now(), revoked_by = %s where id = %s", (user, key)
    )
    with pytest.raises(errors.InsufficientPrivilege), admin_db.transaction():
        admin_db.execute(
            "update website_secret set revoked_at = null, revoked_by = null where id = %s", (key,)
        )


def test_secret_checks(admin_db: psycopg.Connection) -> None:
    user = add_user(admin_db, "k@example.com")
    bad = [
        ("anthropic", b"short", "k1", "AbC9"),
        ("anthropic", SEALED, "k1", "toolong"),
        ("anthropic", SEALED, "bad kek id", "AbC9"),
    ]
    for provider, sealed, kek, last4 in bad:
        with pytest.raises(errors.CheckViolation), admin_db.transaction():
            admin_db.execute(
                "insert into website_secret (provider, version, sealed, kek_id, last4, created_by)"
                " values (%s, 1, %s, %s, %s, %s)",
                (provider, sealed, kek, last4, user),
            )
    with pytest.raises(errors.InvalidTextRepresentation), admin_db.transaction():
        add_secret(admin_db, user, provider="mistral")
