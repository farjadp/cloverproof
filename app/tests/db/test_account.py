"""My account: display name, change password, other sessions revoked (TestClient + real DB)."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from cloverproof_app import account, security

from .conftest import Org
from .test_web_auth import PASSWORD, build_client, email_of, login, page_csrf, with_password

pytestmark = pytest.mark.db

NEW_PASSWORD = "a brand new long passphrase"


def client(db: psycopg.Connection, **overrides: object) -> TestClient:
    test_client = build_client(db, **overrides)
    account.register(test_client.app)  # type: ignore[arg-type]  # no-op once main.py does it
    return test_client


def signed_in(db: psycopg.Connection, user_email: str) -> TestClient:
    c = client(db)
    assert login(c, user_email).status_code == 303
    return c


def change(c: TestClient, current: str, new: str, confirm: str | None = None):  # type: ignore[no-untyped-def]
    return c.post(
        "/account/password",
        data={
            "current_password": current,
            "new_password": new,
            "confirm_password": new if confirm is None else confirm,
            "csrf_token": page_csrf(c, "/account/password"),
        },
    )


def stored_hash(db: psycopg.Connection, org: Org) -> str:
    row = db.execute("select password_hash from app_user where id = %s", (org.agronomist,))
    result = row.fetchone()
    assert result is not None
    return result[0]


@pytest.fixture
def agro_email(db: psycopg.Connection, org_a: Org) -> str:
    with_password(db, org_a.agronomist)
    return email_of(db, org_a.agronomist)


def test_account_page_shows_details(db: psycopg.Connection, org_a: Org, agro_email: str) -> None:
    page = signed_in(db, agro_email).get("/account")
    assert page.status_code == 200
    for text in ("My account", agro_email, "Test org a", "Agronomist", "Agro a"):
        assert text in page.text


def test_edit_display_name(db: psycopg.Connection, org_a: Org, agro_email: str) -> None:
    c = signed_in(db, agro_email)
    token = page_csrf(c, "/account")
    bad = c.post("/account/name", data={"display_name": "   ", "csrf_token": token})
    assert bad.status_code == 422 and "1 to 200 characters" in bad.text
    ok = c.post("/account/name", data={"display_name": " Farjad I. ", "csrf_token": token})
    assert ok.status_code == 303 and ok.headers["location"] == "/account?saved=name"
    assert "Farjad I." in c.get("/account?saved=name").text
    row = db.execute("select display_name from app_user where id = %s", (org_a.agronomist,))
    assert row.fetchone() == ("Farjad I.",)


def test_change_password_ok(db: psycopg.Connection, org_a: Org, agro_email: str) -> None:
    c = signed_in(db, agro_email)
    response = change(c, PASSWORD, NEW_PASSWORD)
    assert response.status_code == 303
    assert response.headers["location"] == "/account?saved=password"
    assert "Password changed" in c.get("/account?saved=password").text
    new_hash = stored_hash(db, org_a)
    assert new_hash.startswith("$argon2id$") and NEW_PASSWORD not in new_hash
    assert login(client(db), agro_email, PASSWORD).status_code == 401
    assert login(client(db), agro_email, NEW_PASSWORD).status_code == 303


def test_change_password_wrong_current(db: psycopg.Connection, org_a: Org, agro_email: str) -> None:
    c = signed_in(db, agro_email)
    before = stored_hash(db, org_a)
    response = change(c, "not my current password", NEW_PASSWORD)
    assert response.status_code == 422 and "Current password is incorrect" in response.text
    assert stored_hash(db, org_a) == before


def test_change_password_wrong_current_is_rate_limited(
    db: psycopg.Connection, agro_email: str
) -> None:
    c = client(db, login_max_failures=2)
    login(c, agro_email)
    for _ in range(2):
        assert change(c, "not my current password", NEW_PASSWORD).status_code == 422
    blocked = change(c, PASSWORD, NEW_PASSWORD)
    assert blocked.status_code == 429 and "Too many wrong attempts" in blocked.text


@pytest.mark.parametrize(
    ("new", "confirm", "message"),
    [
        ("short", None, "at least 12 characters"),
        ("eleven char", None, "at least 12 characters"),
        (NEW_PASSWORD, "something else entirely", "do not match"),
        (PASSWORD, None, "different from the current one"),
    ],
)
def test_change_password_rejected(
    db: psycopg.Connection, org_a: Org, agro_email: str, new: str, confirm: str | None,
    message: str,
) -> None:  # fmt: skip
    c = signed_in(db, agro_email)
    before = stored_hash(db, org_a)
    response = change(c, PASSWORD, new, confirm)
    assert response.status_code == 422 and message in response.text
    assert stored_hash(db, org_a) == before


def test_change_password_revokes_other_sessions_only(
    db: psycopg.Connection, org_a: Org, agro_email: str
) -> None:
    other = signed_in(db, agro_email)
    third = signed_in(db, agro_email)
    current = signed_in(db, agro_email)
    assert change(current, PASSWORD, NEW_PASSWORD).status_code == 303
    assert current.get("/account").status_code == 200
    assert other.get("/").status_code == 401
    assert third.get("/").status_code == 401
    live = db.execute(
        "select token_sha256 from user_session where user_id = %s and revoked_at is null",
        (org_a.agronomist,),
    ).fetchall()
    assert live == [(security.token_sha256(current.cookies["cp_session"]),)]


def test_account_posts_need_csrf(db: psycopg.Connection, org_a: Org, agro_email: str) -> None:
    c = signed_in(db, agro_email)
    before = stored_hash(db, org_a)
    form = {"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    assert (
        c.post("/account/password", data={**form, "confirm_password": NEW_PASSWORD}).status_code
        == 403
    )
    assert c.post("/account/name", data={"display_name": "X"}).status_code == 403
    assert stored_hash(db, org_a) == before


def test_account_needs_sign_in(db: psycopg.Connection) -> None:
    c = client(db)
    for path in ("/account", "/account/password"):
        response = c.get(path, headers={"accept": "text/html"})
        assert response.status_code == 303 and response.headers["location"].startswith("/login")
