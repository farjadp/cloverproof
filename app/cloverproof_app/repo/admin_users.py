"""Account self-service and owner user management. Every member query is org-scoped.

Rules enforced here (not only in the UI):
- an organisation never loses its last enabled owner (demote or disable);
- account-wide actions (password reset, disable) refuse accounts that also belong to
  another organisation, so an owner of one org cannot lock someone out of another;
- only internal roles (owner / agronomist / staff) are managed; `farmer` memberships are
  left as they are.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import class_row

MANAGED_ROLES = ("owner", "agronomist", "staff")


class AdminError(ValueError):
    """A rule was broken. The message is safe to show to the user."""


@dataclass(frozen=True)
class Member:
    id: UUID
    email: str
    display_name: str
    roles: list[str]
    disabled_at: datetime | None
    password_change_required: bool
    has_password: bool
    other_orgs: int


_MEMBER_SELECT = """
select u.id, u.email, u.display_name,
       array_agg(m.role::text order by m.role) as roles,
       u.disabled_at, u.password_change_required,
       (u.password_hash is not null) as has_password,
       (select count(distinct o.organisation_id)::int from membership o
         where o.user_id = u.id and o.organisation_id <> %(org)s) as other_orgs
from membership m join app_user u on u.id = m.user_id
where m.organisation_id = %(org)s
"""


def list_members(conn: psycopg.Connection, org_id: UUID) -> list[Member]:
    """All members of the organisation, disabled ones included."""
    with conn.cursor(row_factory=class_row(Member)) as cur:
        return cur.execute(
            _MEMBER_SELECT + " group by u.id order by lower(u.display_name), u.id",
            {"org": org_id},
        ).fetchall()


def get_member(conn: psycopg.Connection, org_id: UUID, user_id: UUID) -> Member | None:
    """The member, or None when the user is not in this organisation."""
    with conn.cursor(row_factory=class_row(Member)) as cur:
        return cur.execute(
            _MEMBER_SELECT + " and u.id = %(user)s group by u.id",
            {"org": org_id, "user": user_id},
        ).fetchone()


def password_change_required(conn: psycopg.Connection, user_id: UUID) -> bool:
    row = conn.execute(
        "select password_change_required from app_user where id = %s", (user_id,)
    ).fetchone()
    return bool(row and row[0])


def get_password_hash(conn: psycopg.Connection, user_id: UUID) -> str | None:
    row = conn.execute("select password_hash from app_user where id = %s", (user_id,)).fetchone()
    return row[0] if row else None


def set_display_name(conn: psycopg.Connection, user_id: UUID, display_name: str) -> None:
    conn.execute(
        "update app_user set display_name = %s where id = %s", (display_name.strip(), user_id)
    )


def set_own_password(
    conn: psycopg.Connection, *, user_id: UUID, password_hash: str, keep_session_id: UUID
) -> int:
    """User chose their password: store it, clear the flag, revoke other sessions."""
    conn.execute(
        "update app_user set password_hash = %s, password_change_required = false where id = %s",
        (password_hash, user_id),
    )
    return revoke_user_sessions(conn, user_id, except_session_id=keep_session_id)


def set_temporary_password(conn: psycopg.Connection, user_id: UUID, password_hash: str) -> int:
    """Admin-set password: store it, force a change at next sign-in, revoke all sessions."""
    conn.execute(
        "update app_user set password_hash = %s, password_change_required = true where id = %s",
        (password_hash, user_id),
    )
    return revoke_user_sessions(conn, user_id)


def revoke_user_sessions(
    conn: psycopg.Connection, user_id: UUID, *, except_session_id: UUID | None = None
) -> int:
    cur = conn.execute(
        "update user_session set revoked_at = now()"
        " where user_id = %s and revoked_at is null and id is distinct from %s",
        (user_id, except_session_id),
    )
    return cur.rowcount


def email_exists(conn: psycopg.Connection, email: str) -> bool:
    row = conn.execute(
        "select 1 from app_user where lower(email) = lower(%s)", (email.strip(),)
    ).fetchone()
    return row is not None


def create_member(
    conn: psycopg.Connection,
    *,
    org_id: UUID,
    email: str,
    display_name: str,
    role: str,
    temporary_password_hash: str,
) -> UUID:
    if role not in MANAGED_ROLES:
        raise AdminError(f"Role must be one of {', '.join(MANAGED_ROLES)}.")
    if email_exists(conn, email):
        raise AdminError(
            "An account with this email already exists. Ask an administrator to add it to"
            " this organisation with the user-create command."
        )
    row = conn.execute(
        "insert into app_user (email, display_name, password_hash, password_change_required)"
        " values (%s, %s, %s, true) returning id",
        (email.strip(), display_name.strip(), temporary_password_hash),
    ).fetchone()
    assert row is not None
    conn.execute(
        "insert into membership (organisation_id, user_id, role) values (%s, %s, %s)",
        (org_id, row[0], role),
    )
    return row[0]


def _lock_enabled_owners(conn: psycopg.Connection, org_id: UUID) -> set[UUID]:
    """Enabled owners of the org; their membership rows stay locked until commit."""
    rows = conn.execute(
        "select m.user_id from membership m join app_user u on u.id = m.user_id"
        " where m.organisation_id = %s and m.role = 'owner' and u.disabled_at is null"
        " for update of m",
        (org_id,),
    ).fetchall()
    return {r[0] for r in rows}


def _require(member: Member | None) -> Member:
    if member is None:
        raise AdminError("No such member in this organisation.")
    return member


def set_roles(conn: psycopg.Connection, *, org_id: UUID, user_id: UUID, roles: set[str]) -> None:
    """Replace the member's internal roles in this org with `roles` (at least one)."""
    if not roles:
        raise AdminError("Choose at least one role.")
    unknown = roles - set(MANAGED_ROLES)
    if unknown:
        raise AdminError(f"Unknown role: {', '.join(sorted(unknown))}.")
    member = _require(get_member(conn, org_id, user_id))
    owners = _lock_enabled_owners(conn, org_id)
    if "owner" not in roles and owners == {member.id}:
        raise AdminError(
            "This is the last owner of the organisation. Make someone else owner first."
        )
    conn.execute(
        "delete from membership where organisation_id = %s and user_id = %s"
        " and role::text = any(%s) and not (role::text = any(%s))",
        (org_id, user_id, list(MANAGED_ROLES), sorted(roles)),
    )
    for role in sorted(roles):
        conn.execute(
            "insert into membership (organisation_id, user_id, role) values (%s, %s, %s)"
            " on conflict (organisation_id, user_id, role) do nothing",
            (org_id, user_id, role),
        )


def _account_wide_allowed(member: Member) -> None:
    if member.other_orgs:
        raise AdminError(
            "This account also belongs to another organisation, so it can only be reset or"
            " disabled with the user-create command."
        )


def reset_password(
    conn: psycopg.Connection, *, org_id: UUID, user_id: UUID, temporary_password_hash: str
) -> int:
    member = _require(get_member(conn, org_id, user_id))
    _account_wide_allowed(member)
    if member.disabled_at is not None:
        raise AdminError("This account is disabled. Re-enable it first.")
    return set_temporary_password(conn, user_id, temporary_password_hash)


def set_disabled(conn: psycopg.Connection, *, org_id: UUID, user_id: UUID, disabled: bool) -> None:
    member = _require(get_member(conn, org_id, user_id))
    _account_wide_allowed(member)
    if disabled:
        owners = _lock_enabled_owners(conn, org_id)
        if owners == {member.id}:
            raise AdminError(
                "This is the last owner of the organisation. Make someone else owner first."
            )
        conn.execute(
            "update app_user set disabled_at = coalesce(disabled_at, now()) where id = %s",
            (user_id,),
        )
        revoke_user_sessions(conn, user_id)
    else:
        conn.execute("update app_user set disabled_at = null where id = %s", (user_id,))
