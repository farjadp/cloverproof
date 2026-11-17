"""Database access for the web app: one psycopg connection pool per process.

Routes get a connection with `Database.connection()`. The block runs in one transaction:
committed on success, rolled back on any exception. Tests swap in a `Database` that hands
out a single connection inside a rolled-back transaction (see app/tests/db/conftest.py).

Row-level security (ADR 0008, migration 0021): `set_rls_context` is the only place in the
app that sets `app.user_id` / `app.org_id` / `app.platform_role`, always transaction-local
(`set_config(..., true)` with bind parameters), from the server-side session (auth.py).
The settings die with the transaction; the pool's reset callback (`reset_connection`) runs
`RESET ALL` on every returned connection and discards it if a context value survives.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg_pool import ConnectionPool

from cloverproof_app.config import ConfigError

APP_ROLE = "cp_app"
ADMIN_ROLE = "cp_admin"  # CLI login (ADR 0007); the web app must not hold it
RLS_SETTINGS = ("app.user_id", "app.org_id", "app.platform_role")


def set_rls_context(
    conn: psycopg.Connection,
    *,
    user_id: UUID,
    org_id: UUID | None = None,
    platform_role: str | None = None,
) -> None:
    """Set the RLS context for the current transaction only (ADR 0008 §2).

    `org_id` must be an organisation the session user was verified to belong to (auth.py);
    the database checks the membership again (`app_ctx_org()`). An empty string means
    "not set" to the policies, so a call without `org_id` clears an earlier org.
    """
    conn.execute(
        "select set_config('app.user_id', %s, true), set_config('app.org_id', %s, true),"
        " set_config('app.platform_role', %s, true)",
        (str(user_id), str(org_id) if org_id is not None else "", platform_role or ""),
    )


class ContextLeak(RuntimeError):
    """A pooled connection still carried an RLS context after RESET ALL."""


def reset_connection(conn: psycopg.Connection) -> None:
    """Pool `reset` callback: clear session state before the next checkout (ADR 0008 §3).

    Context is transaction-local already; this is the second line for a session-level
    `SET app.*` by mistake. Raising makes the pool discard the connection.
    """
    with conn.transaction():
        conn.execute("reset all")
        row = conn.execute(
            "select " + ", ".join("nullif(current_setting(%s, true), '')" for _ in RLS_SETTINGS),
            RLS_SETTINGS,
        ).fetchone()
    if row is None or any(value is not None for value in row):
        raise ContextLeak("RLS context survived RESET ALL; connection discarded")


def check_least_privilege(conn: psycopg.Connection) -> None:
    """Refuse to run in staging/production as a superuser or outside `cp_app` (review S4).

    As superuser the app could disable the immutability/review triggers; the grants
    (ADR 0002, 0006) only protect anything when the app logs in as a cp_app member.
    """
    try:
        row = conn.execute(
            "select r.rolsuper, r.rolbypassrls, pg_has_role(current_user, %s, 'member'),"
            " case when exists (select 1 from pg_roles where rolname = %s)"
            " then pg_has_role(current_user, %s, 'member') else false end"
            " from pg_roles r where r.rolname = current_user",
            (APP_ROLE, ADMIN_ROLE, ADMIN_ROLE),
        ).fetchone()
    except psycopg.Error as error:
        raise ConfigError(
            f"DATABASE_URL: cannot check the database role ({error.__class__.__name__})"
        ) from error
    if row is None:
        raise ConfigError("DATABASE_URL: the login role was not found in pg_roles")
    superuser, bypassrls, app_member, admin_member = row
    if superuser:
        raise ConfigError("DATABASE_URL logs in as a superuser; use cp_app_login (ADR 0007)")
    if bypassrls:
        raise ConfigError("DATABASE_URL role has BYPASSRLS; use cp_app_login (ADR 0007)")
    if not app_member:
        raise ConfigError(f"DATABASE_URL role is not a member of {APP_ROLE}; use cp_app_login")
    if admin_member:
        raise ConfigError(f"DATABASE_URL role is in {ADMIN_ROLE} (CLI only); use cp_app_login")


class Database(Protocol):
    def open(self) -> None: ...  # pragma: no cover

    def connection(self) -> AbstractContextManager[psycopg.Connection]: ...  # pragma: no cover

    def close(self) -> None: ...  # pragma: no cover


class PooledDatabase:
    def __init__(self, url: str, max_size: int = 5) -> None:
        # open=False: the pool opens on app startup, not at import time.
        self._pool = ConnectionPool(
            url,
            min_size=1,
            max_size=max_size,
            open=False,
            name="cloverproof",
            reset=reset_connection,
        )

    def open(self) -> None:
        # wait=True fails fast at startup when the database is unreachable.
        self._pool.open(wait=True, timeout=10)

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        # The pool's context manager commits on success and rolls back on error.
        with self._pool.connection() as conn:
            yield conn

    def close(self) -> None:
        self._pool.close()
