"""The app shell on real pages: navigation by role, no-organisation route, error pages."""

from __future__ import annotations

from uuid import UUID

import psycopg
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from cloverproof_app import account
from cloverproof_app.auth import current_org

from .conftest import Org
from .test_superadmin import make_user
from .test_web_auth import PASSWORD, build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

HTML = {"Accept": "text/html"}
MAIN_NAV = 'aria-label="Main"'
NEW_PASSWORD = "a brand new long passphrase"


def client_for(db: psycopg.Connection, user: UUID) -> tuple[TestClient, object]:
    with_password(db, user)
    client = build_client(db)
    account.register(client.app)  # type: ignore[arg-type]  # no-op once main.py does it
    return client, login(client, email_of(db, user))


def signed_in(db: psycopg.Connection, user: UUID) -> TestClient:
    client, response = client_for(db, user)
    assert response.status_code == 303  # type: ignore[attr-defined]
    return client


def no_org_superadmin(db: psycopg.Connection, org: Org) -> UUID:
    return make_user(db, org, "no-org-admin", roles=())


def member(db: psycopg.Connection, org: Org, label: str, role: str) -> UUID:
    return make_user(db, org, label, roles=(role,), platform_role=None)


def test_no_organisation_lands_on_products(db: psycopg.Connection, org_a: Org) -> None:
    _, response = client_for(db, no_org_superadmin(db, org_a))
    assert response.headers["location"] == "/products"  # type: ignore[attr-defined]


def test_member_still_lands_on_home(db: psycopg.Connection, org_a: Org) -> None:
    _, response = client_for(db, member(db, org_a, "plain-advisor", "advisor"))
    assert response.headers["location"] == "/"  # type: ignore[attr-defined]


def test_no_organisation_navigation_and_message(db: psycopg.Connection, org_a: Org) -> None:
    client = signed_in(db, no_org_superadmin(db, org_a))
    products = client.get("/products", headers=HTML).text
    assert MAIN_NAV in products and "No organisation" in products
    assert 'href="/farmers"' not in products and 'href="/account/password"' in products

    page = client.get("/", headers=HTML)
    assert page.status_code == 403
    assert "This page needs an organisation" in page.text
    assert "not a member of any organisation" in page.text and 'href="/products"' in page.text


def test_no_organisation_password_change_stays_usable(db: psycopg.Connection, org_a: Org) -> None:
    client = signed_in(db, no_org_superadmin(db, org_a))
    response = client.post(
        "/account/password",
        data={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
            "csrf_token": page_csrf(client, "/account/password"),
        },
        headers=HTML,
    )
    assert response.status_code == 200 and account.PASSWORD_SAVED in response.text


@pytest.mark.parametrize(
    ("role", "sees_users", "sees_review"),
    [("org_admin", True, False), ("agronomist", False, True), ("advisor", False, False)],
)
def test_links_match_what_the_routes_allow(
    db: psycopg.Connection, org_a: Org, role: str, sees_users: bool, sees_review: bool
) -> None:
    client = signed_in(db, member(db, org_a, f"nav-{role}".replace("_", "-"), role))
    page = client.get("/farmers", headers=HTML).text
    assert MAIN_NAV in page and 'href="/products"' in page and 'href="/account"' in page
    assert ('href="/admin/users"' in page) is sees_users
    assert ('href="/review"' in page) is sees_review
    # A hidden link is not the access control: the routes answer the same way.
    assert (client.get("/admin/users", headers=HTML).status_code == 200) is sees_users
    assert (client.get("/review", headers=HTML).status_code == 200) is sees_review


def test_password_page_keeps_full_navigation(db: psycopg.Connection, org_a: Org) -> None:
    client = signed_in(db, member(db, org_a, "nav-admin-pw", "org_admin"))
    page = client.get("/account/password", headers=HTML).text
    assert 'href="/admin/users"' in page and 'aria-label="Breadcrumb"' in page


def test_temporary_password_hides_navigation(db: psycopg.Connection, org_a: Org) -> None:
    user = member(db, org_a, "nav-temp", "advisor")
    client = signed_in(db, user)
    db.execute("update app_user set password_change_required = true where id = %s", (user,))
    page = client.get("/account/password", headers=HTML).text
    assert MAIN_NAV not in page and "Sign out" in page


def test_unknown_page_keeps_navigation(db: psycopg.Connection, org_a: Org) -> None:
    client = signed_in(db, member(db, org_a, "nav-404", "advisor"))
    page = client.get("/no-such-page", headers=HTML)
    assert page.status_code == 404
    assert "Page not found" in page.text and MAIN_NAV in page.text


def test_unknown_page_signed_out_offers_sign_in(db: psycopg.Connection) -> None:
    page = build_client(db).get("/no-such-page", headers=HTML)
    assert page.status_code == 404
    assert MAIN_NAV not in page.text and 'href="/login"' in page.text


def test_server_error_page_keeps_navigation(db: psycopg.Connection, org_a: Org) -> None:
    signed = signed_in(db, member(db, org_a, "nav-500", "advisor"))
    app = signed.app

    @app.get("/test/boom", dependencies=[Depends(current_org)])  # type: ignore[attr-defined]
    def boom() -> None:
        raise RuntimeError("synthetic failure")

    client = TestClient(app, base_url="https://testserver", raise_server_exceptions=False)  # type: ignore[arg-type]
    client.cookies = signed.cookies
    page = client.get("/test/boom", headers=HTML)
    assert page.status_code == 500
    assert "Something went wrong" in page.text and MAIN_NAV in page.text
    assert "synthetic failure" not in page.text


def test_bad_link_is_a_page_not_json(db: psycopg.Connection, org_a: Org) -> None:
    client = signed_in(db, member(db, org_a, "nav-422", "advisor"))
    page = client.get("/farmers/not-an-id", headers=HTML)
    assert page.status_code == 422 and page.headers["content-type"].startswith("text/html")
    assert "This link does not work" in page.text and MAIN_NAV in page.text
    assert "not-an-id" not in page.text
    api_style = client.get("/farmers/not-an-id", headers={"Accept": "application/json"})
    assert api_style.status_code == 422 and api_style.headers["content-type"].startswith(
        "application/json"
    )
