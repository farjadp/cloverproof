"""S2-DB-15: who can read an access grant (migrations 0020, 0021, 0028). The write rules
(one-time revoke, no delete, no scope change) are in test_s2_model.py."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import psycopg
import pytest

from .conftest import Org, insert, use_context

pytestmark = pytest.mark.db


@dataclass
class Grants:
    grantor: UUID
    other_farmer: UUID
    grantee_user: UUID
    farmer_in_grantee_org: UUID
    outsider: UUID
    outsider_org: UUID
    to_user: UUID
    to_org: UUID


def member(db: psycopg.Connection, org: UUID, label: str, role: str) -> UUID:
    user = insert(db, "app_user", email=f"{label}@example.org", display_name=label)
    insert(db, "membership", organisation_id=org, user_id=user, role=role)
    return user


def new_grant(db: psycopg.Connection, org: Org, by: UUID, column: str, grantee: UUID) -> UUID:
    row = db.execute(
        f"insert into access_grant (owner_organisation_id, farmer_id, {column}, scope,"  # type: ignore[arg-type]
        " granted_by) values (%s, %s, %s, 'view', %s) returning id",
        (org.id, org.farmer, grantee, by),
    ).fetchone()
    assert row is not None
    return row[0]


@pytest.fixture
def grants(db: psycopg.Connection, org_a: Org, org_b: Org) -> Grants:
    grantor = member(db, org_a.id, "grantor", "farmer")
    db.execute("update farmer set app_user_id = %s where id = %s", (grantor, org_a.farmer))
    other_farmer = member(db, org_a.id, "other-farmer", "farmer")
    insert(
        db,
        "farmer",
        organisation_id=org_a.id,
        display_name="Other farmer",
        app_user_id=other_farmer,
    )
    grantee_user = member(db, org_b.id, "grantee-user", "advisor")
    farmer_in_grantee_org = member(db, org_b.id, "farmer-b", "farmer")
    outsider_org = insert(db, "organisation", name="Org C")
    outsider = member(db, outsider_org, "outsider", "org_admin")
    use_context(db, grantor, org_a.id)
    return Grants(
        grantor=grantor,
        other_farmer=other_farmer,
        grantee_user=grantee_user,
        farmer_in_grantee_org=farmer_in_grantee_org,
        outsider=outsider,
        outsider_org=outsider_org,
        to_user=new_grant(db, org_a, grantor, "grantee_user_id", grantee_user),
        to_org=new_grant(db, org_a, grantor, "grantee_organisation_id", org_b.id),
    )


def visible(db: psycopg.Connection, user: UUID, org: UUID) -> set[UUID]:
    use_context(db, user, org)
    return {row[0] for row in db.execute("select id from access_grant").fetchall()}


# --- Allowed ----------------------------------------------------------------------------


def test_grantor_reads_the_grants_of_their_own_farmer_record(
    db: psycopg.Connection, org_a: Org, grants: Grants
) -> None:
    assert visible(db, grants.grantor, org_a.id) == {grants.to_user, grants.to_org}


def test_owner_organisation_staff_read_its_grants(
    db: psycopg.Connection, org_a: Org, grants: Grants
) -> None:
    for user in (org_a.staff, org_a.agronomist):
        assert visible(db, user, org_a.id) == {grants.to_user, grants.to_org}


def test_grantee_user_reads_their_grant_only(
    db: psycopg.Connection, org_b: Org, grants: Grants
) -> None:
    # Also a member of the grantee organisation, so the organisation's grant is visible too.
    assert visible(db, grants.grantee_user, org_b.id) == {grants.to_user, grants.to_org}


def test_grantee_organisation_member_reads_the_organisation_grant_only(
    db: psycopg.Connection, org_b: Org, grants: Grants
) -> None:
    assert visible(db, org_b.staff, org_b.id) == {grants.to_org}


def test_farmer_member_who_is_the_grantee_reads_that_grant(
    db: psycopg.Connection, org_a: Org, org_b: Org, grants: Grants
) -> None:
    use_context(db, grants.grantor, org_a.id)
    own = new_grant(db, org_a, grants.grantor, "grantee_user_id", grants.farmer_in_grantee_org)
    assert visible(db, grants.farmer_in_grantee_org, org_b.id) == {own}


def test_revoked_grant_stays_readable_with_its_original_values(
    db: psycopg.Connection, org_a: Org, org_b: Org, grants: Grants
) -> None:
    columns = "farmer_id, grantee_user_id, scope, granted_by, granted_at, expires_at"
    query = f"select {columns} from access_grant where id = %s"
    before = db.execute(query, (grants.to_user,)).fetchone()  # type: ignore[arg-type]
    db.execute(
        "update access_grant set revoked_at = now(), revoked_by = %s,"
        " revoke_reason = 'Changed advisor' where id = %s",
        (grants.grantor, grants.to_user),
    )
    assert db.execute(query, (grants.to_user,)).fetchone() == before  # type: ignore[arg-type]
    assert grants.to_user in visible(db, grants.grantee_user, org_b.id)


# --- Denied -----------------------------------------------------------------------------


def test_another_farmer_of_the_same_organisation_reads_nothing(
    db: psycopg.Connection, org_a: Org, grants: Grants
) -> None:
    assert visible(db, grants.other_farmer, org_a.id) == set()


def test_another_farmer_cannot_revoke(db: psycopg.Connection, org_a: Org, grants: Grants) -> None:
    use_context(db, grants.other_farmer, org_a.id)
    cur = db.execute(
        "update access_grant set revoked_at = now(), revoked_by = %s, revoke_reason = 'x'"
        " where id = %s",
        (grants.other_farmer, grants.to_user),
    )
    assert cur.rowcount == 0


def test_farmer_member_of_the_grantee_organisation_reads_nothing(
    db: psycopg.Connection, org_b: Org, grants: Grants
) -> None:
    assert visible(db, grants.farmer_in_grantee_org, org_b.id) == set()


def test_user_of_an_unrelated_organisation_reads_nothing(
    db: psycopg.Connection, grants: Grants
) -> None:
    assert visible(db, grants.outsider, grants.outsider_org) == set()


def test_no_policy_on_another_table_depends_on_grants(db: psycopg.Connection) -> None:
    row = db.execute(
        "select count(*) from pg_policies where tablename <> 'access_grant'"
        " and (coalesce(qual, '') like '%%access_grant%%'"
        " or coalesce(with_check, '') like '%%access_grant%%')"
    ).fetchone()
    assert row == (0,)
