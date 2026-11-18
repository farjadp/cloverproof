"""A human superadmin creates or joins an organisation (migration 0029, orgs_web.py).

Everything runs as cp_app with the RLS context set, like the app. The role can never be
`agronomist`: a superadmin's approvals must stay out of the calibration data (rule 8).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import errors

from cloverproof_app import account
from cloverproof_app.repo import organisations

from .conftest import Org, as_owner, use_context
from .test_superadmin import make_user, review, service_superadmin_allowed
from .test_web_auth import build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

HTML = {"Accept": "text/html"}
PAGE = "/admin/organisations"
CREATE = "select superadmin_create_organisation(%s, %s, %s)"
JOIN = "select superadmin_join_organisation(%s, %s, %s)"


@pytest.fixture
def superadmin(db: psycopg.Connection, org_a: Org) -> UUID:
    """A human superadmin in no organisation, acting as themselves."""
    user = make_user(db, org_a, "platform-admin", roles=())
    use_context(db, user, platform_role="superadmin")
    return user


def roles_of(db: psycopg.Connection, org_id: UUID, user: UUID) -> list[str]:
    rows = db.execute(
        "select role::text from membership where organisation_id = %s and user_id = %s"
        " order by role",
        (org_id, user),
    ).fetchall()
    return [r[0] for r in rows]


def org_named(db: psycopg.Connection, name: str) -> UUID | None:
    row = db.execute("select id from organisation where name = %s", (name,)).fetchone()
    return row[0] if row else None


def events(db: psycopg.Connection, org_id: UUID) -> list[tuple[Any, ...]]:
    return db.execute(
        "select action, actor_user_id, target_user_id, new_value, actor_db_role = session_user"
        " from admin_event where organisation_id = %s order by at, id",
        (org_id,),
    ).fetchall()


def refused(db: psycopg.Connection, query: str, params: tuple[Any, ...]) -> None:
    with pytest.raises(errors.InsufficientPrivilege), db.transaction():
        db.execute(query, params)


# ---------------------------------------------------------------- database: allowed


def test_superadmin_creates_and_is_a_member(db: psycopg.Connection, superadmin: UUID) -> None:
    row = db.execute(CREATE, (superadmin, "  New Co  ", "org_admin")).fetchone()
    assert row is not None
    assert org_named(db, "New Co") == row[0]  # stored trimmed
    assert roles_of(db, row[0], superadmin) == ["org_admin"]


def test_superadmin_joins_as_either_role(
    db: psycopg.Connection, superadmin: UUID, org_a: Org
) -> None:
    assert db.execute(JOIN, (superadmin, org_a.id, "advisor")).fetchone() == (True,)
    assert db.execute(JOIN, (superadmin, org_a.id, "org_admin")).fetchone() == (True,)
    assert set(roles_of(db, org_a.id, superadmin)) == {"org_admin", "advisor"}


def test_double_join_is_harmless_and_audited_once(
    db: psycopg.Connection, superadmin: UUID, org_a: Org
) -> None:
    before = len(events(db, org_a.id))
    db.execute(JOIN, (superadmin, org_a.id, "advisor"))
    assert db.execute(JOIN, (superadmin, org_a.id, "advisor")).fetchone() == (False,)
    assert roles_of(db, org_a.id, superadmin) == ["advisor"]
    assert len(events(db, org_a.id)) == before + 1


def test_duplicate_name_is_refused_ignoring_case(
    db: psycopg.Connection, superadmin: UUID, org_a: Org
) -> None:
    with pytest.raises(errors.UniqueViolation) as caught, db.transaction():
        db.execute(CREATE, (superadmin, " TEST ORG A ", "advisor"))
    assert caught.value.diag.constraint_name == "organisation_name_taken"


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
def test_bad_name_is_refused(db: psycopg.Connection, superadmin: UUID, name: str) -> None:
    with pytest.raises(errors.CheckViolation), db.transaction():
        db.execute(CREATE, (superadmin, name, "advisor"))


def test_unknown_organisation(db: psycopg.Connection, superadmin: UUID) -> None:
    with pytest.raises(errors.NoDataFound), db.transaction():
        db.execute(JOIN, (superadmin, uuid4(), "advisor"))


# ---------------------------------------------------------------- database: refused


@pytest.mark.parametrize("role", ["org_admin", "agronomist", "advisor", "farmer"])
def test_org_roles_are_refused(db: psycopg.Connection, org_a: Org, org_b: Org, role: str) -> None:
    user = make_user(db, org_a, f"plain-{role}", roles=(role,), platform_role=None)
    use_context(db, user, org_a.id)
    refused(db, CREATE, (user, "Not allowed", "advisor"))
    refused(db, JOIN, (user, org_b.id, "advisor"))
    assert roles_of(db, org_b.id, user) == [] and org_named(db, "Not allowed") is None


def test_service_account_is_refused(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    user = make_user(db, org_a, "ai-svc", roles=(), platform_role=None, actor_kind="service")
    use_context(db, user)
    refused(db, CREATE, (user, "Not allowed", "advisor"))
    refused(db, JOIN, (user, org_b.id, "advisor"))


def test_service_account_with_platform_role_is_refused(db: psycopg.Connection, org_a: Org) -> None:
    with service_superadmin_allowed(db):
        user = make_user(db, org_a, "ai-root", roles=(), actor_kind="service")
        use_context(db, user)
        refused(db, JOIN, (user, org_a.id, "advisor"))


def test_disabled_superadmin_is_refused(
    db: psycopg.Connection, superadmin: UUID, org_a: Org
) -> None:
    with as_owner(db):
        db.execute("update app_user set disabled_at = now() where id = %s", (superadmin,))
    refused(db, JOIN, (superadmin, org_a.id, "advisor"))


def test_spoofed_actor_is_refused(db: psycopg.Connection, superadmin: UUID, org_a: Org) -> None:
    use_context(db, org_a.staff, org_a.id)  # signed in as someone else, naming the superadmin
    refused(db, CREATE, (superadmin, "Spoofed", "advisor"))
    refused(db, JOIN, (superadmin, org_a.id, "advisor"))
    use_context(db, None)  # no signed-in user at all
    refused(db, JOIN, (superadmin, org_a.id, "advisor"))
    assert roles_of(db, org_a.id, superadmin) == []


@pytest.mark.parametrize("role", ["agronomist", "farmer"])
def test_database_refuses_other_roles(
    db: psycopg.Connection, superadmin: UUID, org_a: Org, role: str
) -> None:
    refused(db, CREATE, (superadmin, "Wrong role", role))
    refused(db, JOIN, (superadmin, org_a.id, role))
    assert roles_of(db, org_a.id, superadmin) == [] and org_named(db, "Wrong role") is None


def test_cp_app_still_cannot_write_directly(db: psycopg.Connection, superadmin: UUID) -> None:
    refused(db, "insert into organisation (name) values ('Direct')", ())
    refused(db, "select superadmin_org_check(%s, 'advisor')", (superadmin,))


def test_functions_are_definer_pinned_and_granted_to_cp_app_only(db: psycopg.Connection) -> None:
    rows = db.execute(
        "select p.proname, p.prosecdef, p.proconfig, pg_get_userbyid(p.proowner),"
        " has_function_privilege('cp_app', p.oid, 'execute'),"
        " has_function_privilege('cp_website', p.oid, 'execute'),"
        " exists (select 1 from aclexplode(p.proacl) a where a.grantee = 0)"
        " from pg_proc p where p.proname in"
        " ('superadmin_create_organisation', 'superadmin_join_organisation') order by 1"
    ).fetchall()
    assert len(rows) == 2
    for row in rows:
        assert row[1:] == (True, ['search_path=""'], "cp_migrator", True, False, False)


# ---------------------------------------------------------------- audit and rule 8


def test_create_writes_both_audit_rows(db: psycopg.Connection, superadmin: UUID) -> None:
    row = db.execute(CREATE, (superadmin, "Audited Co", "org_admin")).fetchone()
    assert row is not None
    assert events(db, row[0]) == [
        ("organisation_created", superadmin, superadmin, None, True),
        ("membership_granted", superadmin, superadmin, {"role": "org_admin"}, True),
    ]


def test_join_writes_an_audit_row(db: psycopg.Connection, superadmin: UUID, org_a: Org) -> None:
    db.execute(JOIN, (superadmin, org_a.id, "advisor"))
    assert events(db, org_a.id)[-1] == (
        "membership_granted",
        superadmin,
        superadmin,
        {"role": "advisor"},
        True,
    )


@pytest.mark.parametrize("role", ["org_admin", "advisor"])
def test_joined_superadmin_never_counts_as_agronomist(
    db: psycopg.Connection, superadmin: UUID, org_a: Org, role: str
) -> None:
    db.execute(JOIN, (superadmin, org_a.id, role))
    review_id = review(db, org_a, superadmin, "approve")
    use_context(db, superadmin, org_a.id)
    row = db.execute("select review_kind from review where id = %s", (review_id,)).fetchone()
    assert row == ("superadmin_approved",)
    diff = db.execute(
        "select count(*) from recommendation_diff where approved_by = %s", (superadmin,)
    ).fetchone()
    assert diff == (0,)


def test_list_shows_names_and_own_roles_only(
    db: psycopg.Connection, superadmin: UUID, org_a: Org, org_b: Org
) -> None:
    db.execute(JOIN, (superadmin, org_a.id, "advisor"))
    rows = {r.id: r for r in organisations.list_all(db, superadmin)}
    assert rows[org_a.id].my_roles == ["advisor"] and rows[org_b.id].my_roles == []
    assert rows[org_b.id].name == "Test org b"


# ---------------------------------------------------------------- web


def signed_in(db: psycopg.Connection, user: UUID) -> TestClient:
    with_password(db, user)
    client = build_client(db)
    account.register(client.app)  # type: ignore[arg-type]
    assert login(client, email_of(db, user)).status_code == 303
    return client


def post(client: TestClient, path: str, **data: str) -> Any:
    token = page_csrf(client, PAGE)
    return client.post(path, data={"csrf_token": token, **data}, headers=HTML)


@pytest.mark.parametrize("role", ["org_admin", "agronomist", "advisor", "farmer"])
def test_page_is_superadmin_only(db: psycopg.Connection, org_a: Org, role: str) -> None:
    user = make_user(db, org_a, f"web-{role}", roles=(role,), platform_role=None)
    client = signed_in(db, user)
    assert client.get(PAGE, headers=HTML).status_code == 403
    token = page_csrf(client, "/products")
    data = {"csrf_token": token, "name": "Nope", "role": "advisor"}
    assert client.post(PAGE, data=data, headers=HTML).status_code == 403
    join = client.post(
        f"{PAGE}/{org_a.id}/join", data={"csrf_token": token, "role": "advisor"}, headers=HTML
    )
    assert join.status_code == 403
    assert org_named(db, "Nope") is None
    assert f'href="{PAGE}"' not in client.get("/products", headers=HTML).text


def test_signed_out_is_sent_to_login(db: psycopg.Connection) -> None:
    response = build_client(db).get(PAGE, headers=HTML)
    assert response.status_code == 303 and "/login" in response.headers["location"]


def test_no_organisation_points_to_the_page(db: psycopg.Connection, superadmin: UUID) -> None:
    client = signed_in(db, superadmin)
    assert "Create or join one" in client.get("/products", headers=HTML).text
    assert f'href="{PAGE}"' in client.get("/orgs/choose", headers=HTML).text
    error = client.get("/", headers=HTML)
    assert error.status_code == 403 and "Create or join an organisation" in error.text


def test_other_users_without_organisation_are_not_pointed_there(
    db: psycopg.Connection, org_a: Org
) -> None:
    user = make_user(db, org_a, "no-org-user", roles=(), platform_role=None)
    client = signed_in(db, user)
    for path in ("/products", "/orgs/choose", "/"):
        assert PAGE not in client.get(path, headers=HTML).text


def test_web_create_makes_it_the_current_organisation(
    db: psycopg.Connection, superadmin: UUID, org_a: Org
) -> None:
    client = signed_in(db, superadmin)
    db.execute(JOIN, (superadmin, org_a.id, "advisor"))  # already works elsewhere
    response = post(client, PAGE, name="Fresh Farm Co", role="org_admin")
    assert response.status_code == 303 and response.headers["location"] == f"{PAGE}?done=created"
    org_id = org_named(db, "Fresh Farm Co")
    assert org_id is not None and roles_of(db, org_id, superadmin) == ["org_admin"]
    page = client.get(response.headers["location"], headers=HTML).text
    assert "Organisation created" in page and "Current organisation: <strong>Fresh Farm Co" in page
    assert client.get("/admin/users", headers=HTML).status_code == 200  # usable straight away


def test_web_join_is_usable_straight_away(
    db: psycopg.Connection, superadmin: UUID, org_a: Org
) -> None:
    client = signed_in(db, superadmin)
    assert client.get("/farmers", headers=HTML).status_code == 403
    response = post(client, f"{PAGE}/{org_a.id}/join", role="advisor")
    assert response.status_code == 303 and response.headers["location"] == f"{PAGE}?done=joined"
    assert roles_of(db, org_a.id, superadmin) == ["advisor"]
    assert "Farmer a" in client.get("/farmers", headers=HTML).text


def test_web_list_has_no_farm_data(db: psycopg.Connection, superadmin: UUID, org_a: Org) -> None:
    page = signed_in(db, superadmin).get(PAGE, headers=HTML)
    assert page.status_code == 200 and "Test org a" in page.text and "Not a member" in page.text
    assert "Farmer a" not in page.text and "Farm a" not in page.text
    assert "audit log" in page.text


@pytest.mark.parametrize("role", ["agronomist", "farmer", ""])
def test_web_refuses_other_roles_inline(
    db: psycopg.Connection, superadmin: UUID, org_a: Org, role: str
) -> None:
    client = signed_in(db, superadmin)
    joined = post(client, f"{PAGE}/{org_a.id}/join", role=role)
    assert joined.status_code == 422 and "Choose Org admin or Advisor" in joined.text
    created = post(client, PAGE, name="Role Test", role=role)
    assert created.status_code == 422 and 'value="Role Test"' in created.text
    assert roles_of(db, org_a.id, superadmin) == [] and org_named(db, "Role Test") is None


def test_agronomist_is_never_offered(db: psycopg.Connection, superadmin: UUID, org_a: Org) -> None:
    page = signed_in(db, superadmin).get(PAGE, headers=HTML).text
    assert 'value="agronomist"' not in page and 'value="farmer"' not in page


@pytest.mark.parametrize(
    ("name", "status", "message"),
    [
        ("  ", 422, "Enter a name"),
        ("x" * 201, 422, "Enter a name"),
        ("Line\nbreak", 422, "Enter a name"),
        ("TEST ORG A", 409, "already exists"),
    ],
)
def test_web_name_errors_are_inline(
    db: psycopg.Connection, superadmin: UUID, org_a: Org, name: str, status: int, message: str
) -> None:
    response = post(signed_in(db, superadmin), PAGE, name=name, role="advisor")
    assert response.status_code == status
    assert message in response.text and 'aria-invalid="true"' in response.text


def test_web_join_unknown_organisation(db: psycopg.Connection, superadmin: UUID) -> None:
    response = post(signed_in(db, superadmin), f"{PAGE}/{uuid4()}/join", role="advisor")
    assert response.status_code == 404


def test_web_double_join_says_so(db: psycopg.Connection, superadmin: UUID, org_a: Org) -> None:
    client = signed_in(db, superadmin)
    post(client, f"{PAGE}/{org_a.id}/join", role="advisor")
    again = post(client, f"{PAGE}/{org_a.id}/join", role="advisor")
    assert again.status_code == 303 and again.headers["location"] == f"{PAGE}?done=already"


def test_posts_need_the_csrf_token(db: psycopg.Connection, superadmin: UUID, org_a: Org) -> None:
    client = signed_in(db, superadmin)
    created = client.post(PAGE, data={"name": "No Token", "role": "advisor"}, headers=HTML)
    joined = client.post(f"{PAGE}/{org_a.id}/join", data={"role": "advisor"}, headers=HTML)
    assert created.status_code == joined.status_code == 403
    assert org_named(db, "No Token") is None and roles_of(db, org_a.id, superadmin) == []


def test_platform_role_removed_mid_session_is_refused(
    db: psycopg.Connection, superadmin: UUID, org_a: Org
) -> None:
    client = signed_in(db, superadmin)
    token = page_csrf(client, PAGE)
    with as_owner(db):
        db.execute("update app_user set platform_role = null where id = %s", (superadmin,))
    response = client.post(
        f"{PAGE}/{org_a.id}/join", data={"csrf_token": token, "role": "advisor"}, headers=HTML
    )
    assert response.status_code == 403 and roles_of(db, org_a.id, superadmin) == []
