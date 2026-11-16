"""Server-side sessions in `user_session`. Only the SHA-256 of the cookie token is stored."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class SessionUser:
    session_id: UUID
    user_id: UUID
    email: str
    display_name: str
    last_seen_at: datetime


def create_session(
    conn: psycopg.Connection, *, user_id: UUID, token_sha256: str, absolute: timedelta
) -> UUID:
    row = conn.execute(
        "insert into user_session (user_id, token_sha256, expires_at)"
        " values (%s, %s, now() + %s) returning id",
        (user_id, token_sha256, absolute),
    ).fetchone()
    assert row is not None
    return row[0]


def get_active_session(
    conn: psycopg.Connection, *, token_sha256: str, idle: timedelta
) -> SessionUser | None:
    """A live session: not revoked, not past absolute or idle expiry, user not disabled."""
    with conn.cursor(row_factory=class_row(SessionUser)) as cur:
        return cur.execute(
            "select s.id as session_id, u.id as user_id, u.email, u.display_name,"
            " s.last_seen_at"
            " from user_session s join app_user u on u.id = s.user_id"
            " where s.token_sha256 = %s and s.revoked_at is null"
            " and s.expires_at > now() and s.last_seen_at > now() - %s"
            " and u.disabled_at is null",
            (token_sha256, idle),
        ).fetchone()


def touch_session(conn: psycopg.Connection, session_id: UUID) -> None:
    conn.execute("update user_session set last_seen_at = now() where id = %s", (session_id,))


def revoke_session(conn: psycopg.Connection, *, token_sha256: str) -> None:
    conn.execute(
        "update user_session set revoked_at = now() where token_sha256 = %s and revoked_at is null",
        (token_sha256,),
    )


def revoke_all_for_user(conn: psycopg.Connection, user_id: UUID) -> int:
    """Sign the user out everywhere (security review S3). Returns how many were live."""
    cur = conn.execute(
        "update user_session set revoked_at = now() where user_id = %s and revoked_at is null",
        (user_id,),
    )
    return cur.rowcount
