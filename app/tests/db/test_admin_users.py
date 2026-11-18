"""Org admin user management and admin-driven recovery (TestClient + real DB)."""

from __future__ import annotations

import re
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient

from cloverproof_app import account, cli, security
from cloverproof_app.repo import admin_users

from .conftest import Org, as_owner, as_role, insert
from .test_account import NEW_PASSWORD, change, client, signed_in
from .test_web_auth import PASSWORD, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

OWNER_EMAIL = "owner-a@example.org"
TEMP_RE = re.compile(r"<code>([A-Za-z0-9-]+)</code>")


@pytest.fixture
def owner(db: psycopg.Connection, org_a: Org) -> UUID:
    user = insert(db, "app_user", email=OWNER_EMAIL, display_name="Owner A")
    insert(db, "membership", organisation_id=org_a.id, user_id=user, role="org_admin")
    with_password(db, user)
    return user


def owner_client(db: psycopg.Connection) -> TestClient:
    return signed_in(db, OWNER_EMAIL)


def post(c: TestClient, path: str, **data: object):  # type: ignore[no-untyped-def]
    return c.post(path, data={**data, "csrf_token": page_csrf(c, "/admin/users")})


def flags(db: psycopg.Connection, user_id: UUID) -> tuple[bool, bool, str | None]:
    row = db.execute(
        "select password_change_required, disabled_at is not null, password_hash"
        " from app_user where id = %s",
        (user_id,),
    ).fetchone()
    assert row is not None
    return row


def live_sessions(db: psycopg.Connection, user_id: UUID) -> int:
    row = db.execute(
        "select count(*) from user_session where user_id = %s and revoked_at is null", (user_id,)
    ).fetchone()
    assert row is not None
    return row[0]


def test_temporary_password_is_high_entropy() -> None:
    values = {account.new_temporary_password() for _ in range(50)}
    assert len(values) == 50
    for value in values:
        assert re.fullmatch(r"([a-km-zA-HJ-NP-Z2-9]{5}-){3}[a-km-zA-HJ-NP-Z2-9]{5}", value)


@pytest.mark.parametrize("role", ["agronomist", "advisor"])
def test_non_owner_gets_403(db: psycopg.Connection, org_a: Org, owner: UUID, role: str) -> None:
    user = org_a.agronomist if role == "agronomist" else org_a.staff
    with_password(db, user)
    c = signed_in(db, email_of(db, user))
    assert c.get("/admin/users", headers={"accept": "text/html"}).status_code == 403
    assert c.get(f"/admin/users/{owner}").status_code == 403
    token = page_csrf(c, "/account")
    create = c.post(
        "/admin/users",
        data={
            "email": "x@example.org",
            "display_name": "X",
            "role": "org_admin",
            "csrf_token": token,
        },
    )
    assert create.status_code == 403
    for action in ("reset-password", "disable"):
        assert (
            c.post(f"/admin/users/{owner}/{action}", data={"csrf_token": token}).status_code == 403
        )
    roles = c.post(f"/admin/users/{user}/roles", data={"roles": "org_admin", "csrf_token": token})
    assert roles.status_code == 403
    assert flags(db, owner)[1] is False and not admin_users.email_exists(db, "x@example.org")


def test_owner_lists_only_own_org(
    db: psycopg.Connection, org_a: Org, org_b: Org, owner: UUID
) -> None:
    page = owner_client(db).get("/admin/users")
    assert page.status_code == 200
    assert "Agro a" in page.text and "Staff a" in page.text and "Owner A" in page.text
    assert "Agro b" not in page.text and "agro-b@example.org" not in page.text


def test_cross_org_member_not_visible_or_editable(
    db: psycopg.Connection, org_a: Org, org_b: Org, owner: UUID
) -> None:
    c = owner_client(db)
    target = org_b.agronomist
    with_password(db, target)
    victim = signed_in(db, email_of(db, target))
    before = flags(db, target)
    assert c.get(f"/admin/users/{target}", headers={"accept": "text/html"}).status_code == 404
    for action in ("reset-password", "disable", "enable"):
        assert post(c, f"/admin/users/{target}/{action}").status_code == 404
    assert post(c, f"/admin/users/{target}/roles", roles="org_admin").status_code == 404
    assert flags(db, target) == before
    assert victim.get("/").status_code == 200
    assert not admin_users.get_member(db, org_a.id, target)


def test_owner_creates_user_and_temp_login_forces_change(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    c = owner_client(db)
    response = post(
        c,
        "/admin/users",
        email="New.Person@example.org",
        display_name="New Person",
        role="advisor",
    )
    assert response.status_code == 200 and "shown only now" in response.text
    match = TEMP_RE.search(response.text)
    assert match is not None
    temp = match.group(1)

    row = db.execute(
        "select id, password_hash, password_change_required from app_user"
        " where lower(email) = 'new.person@example.org'"
    ).fetchone()
    assert row is not None
    user_id, stored, required = row
    assert required is True and stored.startswith("$argon2id$") and temp not in stored
    member = admin_users.get_member(db, org_a.id, user_id)
    assert member is not None and member.roles == ["advisor"]
    # Shown once: the list page does not show it again.
    assert temp not in c.get("/admin/users").text

    new = client(db)
    assert login(new, "new.person@example.org", temp).status_code == 303
    home = new.get("/", headers={"accept": "text/html"})
    assert home.status_code == 303 and home.headers["location"] == "/account/password"
    assert (
        new.get("/account", headers={"accept": "text/html"}).headers["location"]
        == "/account/password"
    )
    htmx = new.get("/", headers={"HX-Request": "true"})
    assert htmx.status_code == 403 and htmx.headers["HX-Redirect"] == "/account/password"
    form = new.get("/account/password")
    assert form.status_code == 200 and "set by an administrator" in form.text
    token = page_csrf(new, "/account/password")
    assert (
        new.post("/account/name", data={"display_name": "X", "csrf_token": token}).status_code
        == 403
    )

    assert change(new, temp, NEW_PASSWORD).status_code == 303
    assert flags(db, user_id)[0] is False
    assert new.get("/").status_code == 200
    assert login(client(db), "new.person@example.org", NEW_PASSWORD).status_code == 303


def test_create_user_validation_and_duplicate(
    db: psycopg.Connection, org_a: Org, org_b: Org, owner: UUID
) -> None:
    c = owner_client(db)
    bad = post(c, "/admin/users", email="not-an-email", display_name="", role="farmer")
    assert bad.status_code == 422
    for text in ("Enter an email address", "1 to 200 characters", "Choose a role"):
        assert text in bad.text
    for role in ("agronomist", "org_admin"):
        cli_only = post(c, "/admin/users", email="z@example.org", display_name="Z", role=role)
        assert cli_only.status_code == 422 and "user-create command" in cli_only.text
    assert not admin_users.email_exists(db, "z@example.org")
    # Exists already (even in another org, any case): refused, nothing changed.
    dup = post(c, "/admin/users", email="AGRO-B@example.org", display_name="Dup", role="advisor")
    assert dup.status_code == 409 and "already exists" in dup.text
    assert admin_users.get_member(db, org_a.id, org_b.agronomist) is None


def test_reset_password_revokes_sessions_and_forces_change(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    with_password(db, org_a.staff)
    staff_email = email_of(db, org_a.staff)
    staff = signed_in(db, staff_email)
    signed_in(db, staff_email)
    assert live_sessions(db, org_a.staff) == 2

    response = post(owner_client(db), f"/admin/users/{org_a.staff}/reset-password")
    assert response.status_code == 200 and "shown only now" in response.text
    match = TEMP_RE.search(response.text)
    assert match is not None
    assert live_sessions(db, org_a.staff) == 0
    assert staff.get("/").status_code == 401
    assert flags(db, org_a.staff)[0] is True
    assert login(client(db), staff_email, PASSWORD).status_code == 401
    temp_client = client(db)
    assert login(temp_client, staff_email, match.group(1)).status_code == 303
    assert (
        temp_client.get("/", headers={"accept": "text/html"}).headers["location"]
        == "/account/password"
    )


def test_owner_cannot_reset_own_password_here(db: psycopg.Connection, owner: UUID) -> None:
    response = post(owner_client(db), f"/admin/users/{owner}/reset-password")
    assert response.status_code == 409 and "My account" in response.text
    assert flags(db, owner)[0] is False


def test_account_in_another_org_cannot_be_reset_or_disabled(
    db: psycopg.Connection, org_a: Org, org_b: Org, owner: UUID
) -> None:
    insert(db, "membership", organisation_id=org_b.id, user_id=org_a.staff, role="advisor")
    c = owner_client(db)
    for action in ("reset-password", "disable"):
        response = post(c, f"/admin/users/{org_a.staff}/{action}")
        assert response.status_code == 409 and "another organisation" in response.text
    assert flags(db, org_a.staff)[:2] == (False, False)


def test_disable_revokes_sessions_and_enable_restores(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    with_password(db, org_a.staff)
    staff_email = email_of(db, org_a.staff)
    staff = signed_in(db, staff_email)
    c = owner_client(db)
    response = post(c, f"/admin/users/{org_a.staff}/disable")
    assert response.status_code == 303
    assert "Account disabled" in c.get(response.headers["location"]).text
    assert flags(db, org_a.staff)[1] is True and live_sessions(db, org_a.staff) == 0
    assert staff.get("/").status_code == 401
    assert login(client(db), staff_email).status_code == 401
    # Still listed (disabled), so the owner can re-enable.
    assert "Disabled" in c.get("/admin/users").text
    assert post(c, f"/admin/users/{org_a.staff}/enable").status_code == 303
    assert login(client(db), staff_email).status_code == 303


def test_owner_cannot_change_agronomist_or_owner_roles(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    c = owner_client(db)
    page = c.get(f"/admin/users/{org_a.agronomist}")
    assert "set by a platform administrator" in page.text
    assert 'name="roles" value="agronomist"' not in page.text
    assert 'name="roles" value="org_admin"' not in page.text
    for target, roles in (
        (org_a.staff, ["advisor", "agronomist"]),
        (org_a.staff, ["advisor", "org_admin"]),
        (owner, ["agronomist", "org_admin"]),
    ):
        response = post(c, f"/admin/users/{target}/roles", roles=roles)
        assert response.status_code == 409 and "user-create command" in response.text
    assert admin_users.get_member(db, org_a.id, org_a.staff).roles == ["advisor"]  # type: ignore[union-attr]
    # Not posting a CLI-only role does not remove it.
    assert post(c, f"/admin/users/{owner}/roles").status_code == 303
    assert post(c, f"/admin/users/{org_a.agronomist}/roles", roles="advisor").status_code == 303
    assert admin_users.get_member(db, org_a.id, owner).roles == ["org_admin"]  # type: ignore[union-attr]
    assert admin_users.get_member(db, org_a.id, org_a.agronomist).roles == [  # type: ignore[union-attr]
        "agronomist",
        "advisor",
    ]
    # Re-posting a CLI-only role the member already holds is a no-op, not an error.
    kept = post(c, f"/admin/users/{org_a.agronomist}/roles", roles=["agronomist"])
    assert kept.status_code == 303
    assert admin_users.get_member(db, org_a.id, org_a.agronomist).roles == ["agronomist"]  # type: ignore[union-attr]


def test_owner_cannot_reset_agronomist_or_owner_password(
    db: psycopg.Connection, org_a: Org, owner: UUID
) -> None:
    second = insert(db, "app_user", email="owner2-a@example.org", display_name="Owner 2")
    insert(db, "membership", organisation_id=org_a.id, user_id=second, role="org_admin")
    c = owner_client(db)
    assert "Reset password" not in c.get(f"/admin/users/{org_a.agronomist}").text
    for target in (org_a.agronomist, second):
        before = flags(db, target)
        response = post(c, f"/admin/users/{target}/reset-password")
        assert response.status_code == 409 and "--reset-password" in response.text
        assert flags(db, target) == before


def test_last_owner_cannot_disable_self(db: psycopg.Connection, org_a: Org, owner: UUID) -> None:
    c = owner_client(db)
    disable = post(c, f"/admin/users/{owner}/disable")
    assert disable.status_code == 409 and "last org admin" in disable.text
    assert flags(db, owner)[1] is False
    assert c.get("/admin/users").status_code == 200

    # With a second enabled owner (added by an operator), disabling yourself is allowed.
    insert(db, "membership", organisation_id=org_a.id, user_id=org_a.agronomist, role="org_admin")
    response = post(c, f"/admin/users/{owner}/disable")
    assert response.status_code == 303 and response.headers["location"] == "/login"
    assert flags(db, owner)[1] is True


def test_disabled_owner_does_not_count(db: psycopg.Connection, org_a: Org, owner: UUID) -> None:
    insert(db, "membership", organisation_id=org_a.id, user_id=org_a.staff, role="org_admin")
    with as_owner(db):  # operator setup; cp_app cannot disable approvers (0014)
        db.execute("update app_user set disabled_at = now() where id = %s", (org_a.staff,))
    disable = post(owner_client(db), f"/admin/users/{owner}/disable")
    assert disable.status_code == 409 and "last org admin" in disable.text


def test_roles_set_staff_and_keep_farmer(db: psycopg.Connection, org_a: Org, owner: UUID) -> None:
    insert(db, "membership", organisation_id=org_a.id, user_id=org_a.staff, role="farmer")
    c = owner_client(db)
    none = post(c, f"/admin/users/{org_a.staff}/roles")
    assert none.status_code == 409 and "at least one role" in none.text
    unknown = post(c, f"/admin/users/{org_a.staff}/roles", roles=["farmer"])
    assert unknown.status_code == 409
    member = admin_users.get_member(db, org_a.id, org_a.staff)
    assert member is not None and member.roles == ["advisor", "farmer"]


def test_admin_posts_need_csrf(db: psycopg.Connection, org_a: Org, owner: UUID) -> None:
    c = owner_client(db)
    assert c.post(f"/admin/users/{org_a.staff}/disable").status_code == 403
    no_token = c.post(
        "/admin/users", data={"email": "y@example.org", "display_name": "Y", "role": "advisor"}
    )
    assert no_token.status_code == 403
    assert flags(db, org_a.staff)[1] is False and not admin_users.email_exists(db, "y@example.org")


def test_cli_reset_password_sets_flag_and_revokes(db: psycopg.Connection, org_a: Org) -> None:
    with_password(db, org_a.agronomist)
    agro_email = email_of(db, org_a.agronomist)
    signed = signed_in(db, agro_email)
    with as_role(db, "cp_admin"):  # the CLI logs in as cp_admin_login (ADR 0007)
        result = cli.user_create(
            db, email=agro_email, org=str(org_a.id), role="agronomist", display_name=None,
            create_org=False, reset_password=True, read_password=lambda: "temporary password 1",
        )  # fmt: skip
    assert result.password_set
    required, _, stored = flags(db, org_a.agronomist)
    assert required is True and security.verify_password("temporary password 1", stored)[0]
    assert signed.get("/").status_code == 401
    fresh = client(db)
    assert login(fresh, agro_email, "temporary password 1").status_code == 303
    assert (
        fresh.get("/", headers={"accept": "text/html"}).headers["location"] == "/account/password"
    )
