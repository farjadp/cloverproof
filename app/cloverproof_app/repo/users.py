"""Users and organisations (auth lookups and CLI account creation; not org-scoped)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class UserCredentials:
    id: UUID
    email: str
    password_hash: str | None
    disabled_at: datetime | None
    actor_kind: str  # 'human' | 'service' (migration 0012); only humans sign in (B1)
    temp_password_expired: bool  # admin-set password past temp_password_expires_at (N11)

    @property
    def can_sign_in(self) -> bool:
        return (
            self.disabled_at is None
            and self.actor_kind == "human"
            and not self.temp_password_expired
        )


@dataclass(frozen=True)
class Organisation:
    id: UUID
    name: str


def get_credentials_by_email(conn: psycopg.Connection, email: str) -> UserCredentials | None:
    """Auth lookup. Local accounts only; emails compare case-insensitively."""
    with conn.cursor(row_factory=class_row(UserCredentials)) as cur:
        return cur.execute(
            "select id, email, password_hash, disabled_at, actor_kind,"
            " coalesce(temp_password_expires_at <= now(), false) as temp_password_expired"
            " from app_user"
            " where lower(email) = lower(%s) and auth_provider = 'local'",
            (email.strip(),),
        ).fetchone()


def set_actor(conn: psycopg.Connection, user_id: UUID) -> None:
    """`SET LOCAL app.user_id`: the admin_event triggers (0012, F2) record who acted."""
    conn.execute("select set_config('app.user_id', %s, true)", (str(user_id),))


def create_user(
    conn: psycopg.Connection, *, email: str, display_name: str, password_hash: str
) -> UUID:
    """A human account (CLI, runs as cp_admin). Service accounts are never made here (B1)."""
    row = conn.execute(
        "insert into app_user (email, display_name, password_hash, actor_kind)"
        " values (%s, %s, %s, 'human') returning id",
        (email.strip(), display_name.strip(), password_hash),
    ).fetchone()
    assert row is not None
    return row[0]


def set_password_hash(conn: psycopg.Connection, user_id: UUID, password_hash: str) -> None:
    conn.execute("update app_user set password_hash = %s where id = %s", (password_hash, user_id))


def find_organisation_by_name(conn: psycopg.Connection, name: str) -> list[Organisation]:
    with conn.cursor(row_factory=class_row(Organisation)) as cur:
        return cur.execute(
            "select id, name from organisation where name = %s order by created_at",
            (name.strip(),),
        ).fetchall()


def create_organisation(conn: psycopg.Connection, name: str) -> UUID:
    row = conn.execute(
        "insert into organisation (name) values (%s) returning id", (name.strip(),)
    ).fetchone()
    assert row is not None
    return row[0]


def add_membership(conn: psycopg.Connection, *, org_id: UUID, user_id: UUID, role: str) -> None:
    conn.execute(
        "insert into membership (organisation_id, user_id, role) values (%s, %s, %s)"
        " on conflict (organisation_id, user_id, role) do nothing",
        (org_id, user_id, role),
    )


def user_organisations(conn: psycopg.Connection, user_id: UUID) -> list[Organisation]:
    """Organisations the (enabled) user belongs to, via member_organisation_ids()."""
    with conn.cursor(row_factory=class_row(Organisation)) as cur:
        return cur.execute(
            "select o.id, o.name from organisation o"
            " where o.id in (select member_organisation_ids(%s)) order by o.name, o.id",
            (user_id,),
        ).fetchall()


def has_org_role(conn: psycopg.Connection, *, user_id: UUID, org_id: UUID, role: str) -> bool:
    row = conn.execute("select has_org_role(%s, %s, %s)", (user_id, org_id, role)).fetchone()
    return bool(row and row[0])


def org_roles(conn: psycopg.Connection, *, user_id: UUID, org_id: UUID) -> list[str]:
    rows = conn.execute(
        "select m.role::text from membership m join app_user u on u.id = m.user_id"
        " where m.user_id = %s and m.organisation_id = %s and u.disabled_at is null"
        " order by m.role",
        (user_id, org_id),
    ).fetchall()
    return [r[0] for r in rows]
