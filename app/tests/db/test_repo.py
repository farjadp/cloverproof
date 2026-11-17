"""Data-access layer: org scoping and auth lookups."""

from datetime import timedelta

import psycopg
import pytest

from cloverproof_app.repo import farmers, sessions, users

from .conftest import Org, insert

pytestmark = pytest.mark.db


def test_list_farmers_only_returns_the_given_org(
    db: psycopg.Connection, org_a: Org, org_b: Org
) -> None:
    insert(db, "farmer", organisation_id=org_a.id, display_name="Second farmer a")
    a = farmers.list_farmers(db, org_a.id)
    b = farmers.list_farmers(db, org_b.id)
    assert {f.id for f in a} >= {org_a.farmer}
    assert len(a) == 2 and len(b) == 1
    assert {f.id for f in b} == {org_b.farmer}
    assert not {f.id for f in a} & {f.id for f in b}
    assert next(f for f in a if f.id == org_a.farmer).farm_count == 1


def test_user_organisations_and_roles(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    assert [o.id for o in users.user_organisations(db, org_a.agronomist)] == [org_a.id]
    assert users.has_org_role(db, user_id=org_a.agronomist, org_id=org_a.id, role="agronomist")
    assert not users.has_org_role(db, user_id=org_a.agronomist, org_id=org_b.id, role="agronomist")
    assert not users.has_org_role(db, user_id=org_a.staff, org_id=org_a.id, role="agronomist")
    assert users.org_roles(db, user_id=org_a.staff, org_id=org_a.id) == ["staff"]


def test_email_lookup_is_case_insensitive(db: psycopg.Connection, org_a: Org) -> None:
    found = users.get_credentials_by_email(db, "  AGRO-A@example.org ")
    assert found is not None and found.id == org_a.agronomist


def test_session_lifecycle(db: psycopg.Connection, org_a: Org) -> None:
    token = "a" * 64
    users_session = sessions.create_session(
        db, user_id=org_a.agronomist, token_sha256=token, absolute=timedelta(hours=1)
    )
    live = sessions.get_active_session(db, token_sha256=token, idle=timedelta(minutes=5))
    assert live is not None and live.session_id == users_session
    sessions.revoke_session(db, token_sha256=token)
    assert sessions.get_active_session(db, token_sha256=token, idle=timedelta(minutes=5)) is None
