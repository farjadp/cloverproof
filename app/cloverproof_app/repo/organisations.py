"""Organisations as a superadmin sees them (/admin/organisations).

Not org-scoped on purpose: names and the caller's own roles only, never farm data. Writes go
through the SECURITY DEFINER functions of migration 0029, which check the actor again; cp_app
has no write grant on `organisation` or `membership` (ADR 0007).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import psycopg
from psycopg import errors
from psycopg.rows import class_row

# Never `agronomist`: a superadmin's approvals would count as agronomist approvals (rule 8).
JOIN_ROLES = ("org_admin", "advisor")
NAME_TAKEN_CONSTRAINT = "organisation_name_taken"


class OrganisationNameTaken(ValueError):
    """Another organisation already has this name."""


class NoSuchOrganisation(LookupError):
    """The organisation does not exist."""


@dataclass(frozen=True)
class OrganisationRow:
    id: UUID
    name: str
    my_roles: list[str]


def list_all(conn: psycopg.Connection, user_id: UUID) -> list[OrganisationRow]:
    """Every organisation, with the roles `user_id` holds in it (empty when not a member)."""
    with conn.cursor(row_factory=class_row(OrganisationRow)) as cur:
        return cur.execute(
            "select o.id, o.name,"
            " coalesce(array_agg(m.role::text order by m.role)"
            "          filter (where m.role is not null), '{}') as my_roles"
            " from organisation o"
            " left join membership m on m.organisation_id = o.id and m.user_id = %s"
            " group by o.id order by lower(o.name), o.id",
            (user_id,),
        ).fetchall()


def create(conn: psycopg.Connection, *, actor_id: UUID, name: str, role: str) -> UUID:
    """Create the organisation and add the actor to it. Call inside a savepoint."""
    try:
        row = conn.execute(
            "select superadmin_create_organisation(%s, %s, %s)", (actor_id, name, role)
        ).fetchone()
    except errors.UniqueViolation as error:
        if error.diag.constraint_name == NAME_TAKEN_CONSTRAINT:
            raise OrganisationNameTaken(name) from error
        raise
    assert row is not None
    return row[0]


def join(conn: psycopg.Connection, *, actor_id: UUID, org_id: UUID, role: str) -> bool:
    """Add the actor to the organisation; False when they already held this role."""
    try:
        row = conn.execute(
            "select superadmin_join_organisation(%s, %s, %s)", (actor_id, org_id, role)
        ).fetchone()
    except errors.NoDataFound as error:
        raise NoSuchOrganisation(str(org_id)) from error
    assert row is not None
    return bool(row[0])
