"""Web auth end to end (TestClient + real database): login, sessions, CSRF, roles, orgs."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

import psycopg
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from cloverproof_app import security
from cloverproof_app.auth import OrgContext, require_org_role
from cloverproof_app.main import create_app
from cloverproof_app.repo import users

from ..support.fakes import make_settings
from .conftest import Org, insert

pytestmark = pytest.mark.db

PASSWORD = "correct horse battery staple"
GENERIC_ERROR = "Email or password is incorrect"


class ConnDatabase:
    """Hands the test's connection to the app; each request runs in a savepoint."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with self.conn.transaction():
            yield self.conn


def build_client(db: psycopg.Connection, **overrides: object) -> TestClient:
    app = create_app(make_settings(**overrides), ConnDatabase(db))

    @app.get("/test/agronomist-only")
    def agronomist_only(
        context: Annotated[OrgContext, Depends(require_org_role("agronomist"))],
    ) -> dict[str, str]:
        return {"org": str(context.org.id)}

    # https so the Secure cookie is stored and sent, as in production.
    return TestClient(app, base_url="https://testserver", follow_redirects=False)


def with_password(db: psycopg.Connection, user_id: UUID) -> None:
    users.set_password_hash(db, user_id, security.hash_password(PASSWORD))


def email_of(db: psycopg.Connection, user_id: UUID) -> str:
    row = db.execute("select email from app_user where id = %s", (user_id,)).fetchone()
    assert row is not None
    return row[0]


def login_csrf(client: TestClient) -> str:
    page = client.get("/login")
    assert page.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert match is not None
    return match.group(1)


def login(client: TestClient, email: str, password: str = PASSWORD, **extra: str):  # type: ignore[no-untyped-def]
    token = login_csrf(client)
    return client.post(
        "/login", data={"email": email, "password": password, "csrf_token": token, **extra}
    )


def page_csrf(client: TestClient, path: str = "/") -> str:
    match = re.search(r'"X-CSRF-Token": "([0-9a-f]{64})"', client.get(path).text)
    assert match is not None
    return match.group(1)


@pytest.fixture
def agronomist(db: psycopg.Connection, org_a: Org) -> str:
    with_password(db, org_a.agronomist)
    return email_of(db, org_a.agronomist)


def test_login_ok_shows_only_own_org_farmers(
    db: psycopg.Connection, org_a: Org, org_b: Org, agronomist: str
) -> None:
    client = build_client(db)
    response = login(client, agronomist.upper())
    assert response.status_code == 303 and response.headers["location"] == "/"
    cookie = response.headers["set-cookie"]
    assert "cp_session=" in cookie and "HttpOnly" in cookie and "Secure" in cookie
    assert "SameSite=lax" in cookie or "samesite=lax" in cookie.lower()

    token = client.cookies["cp_session"]
    rows = db.execute(
        "select token_sha256 from user_session where user_id = %s", (org_a.agronomist,)
    )
    stored = [r[0] for r in rows]
    assert stored == [security.token_sha256(token)] and token not in stored

    home = client.get("/")
    assert home.status_code == 200
    assert "Farmers" in home.text and "Farmer a" in home.text
    assert "Farmer b" not in home.text  # org scoping
    assert home.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in home.headers["content-security-policy"]


def test_login_redirects_to_safe_next_only(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(db)
    assert login(client, agronomist, next="/orgs/choose").headers["location"] == "/orgs/choose"
    client = build_client(db)
    assert login(client, agronomist, next="//evil.example").headers["location"] == "/"


@pytest.mark.parametrize("case", ["wrong-password", "unknown-email", "empty"])
def test_login_failure_is_generic(db: psycopg.Connection, agronomist: str, case: str) -> None:
    email, password = {
        "wrong-password": (agronomist, "not the right password"),
        "unknown-email": ("nobody@example.org", PASSWORD),
        "empty": ("", ""),
    }[case]
    client = build_client(db)
    response = login(client, email, password)
    assert response.status_code == 401
    assert GENERIC_ERROR in response.text
    assert "cp_session" not in client.cookies


def test_user_without_password_cannot_log_in(db: psycopg.Connection, org_a: Org) -> None:
    response = login(build_client(db), email_of(db, org_a.staff), PASSWORD)
    assert response.status_code == 401


def test_rate_limit_blocks_even_the_right_password(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(db, login_max_failures=3, login_window_minutes=15)
    for _ in range(3):
        assert login(client, agronomist, "wrong password here").status_code == 401
    blocked = login(client, agronomist, PASSWORD)
    assert blocked.status_code == 429
    assert "Too many attempts" in blocked.text
    assert "cp_session" not in client.cookies
    # Another email from the same client is not blocked.
    assert login(client, "other@example.org", "x" * 12).status_code == 401


def test_idle_session_expires(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(db, session_idle_minutes=30)
    login(client, agronomist)
    assert client.get("/").status_code == 200
    db.execute("update user_session set last_seen_at = now() - interval '31 minutes'")
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 303 and response.headers["location"] == "/login?expired=1"
    assert "You were signed out" in client.get("/login?expired=1").text


def test_absolute_session_expiry(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(db)
    login(client, agronomist)
    db.execute(
        "update user_session set created_at = now() - interval '13 hours',"
        " expires_at = now() - interval '1 hour', last_seen_at = now()"
    )
    assert client.get("/", headers={"accept": "text/html"}).status_code == 303


def test_unauthenticated_requests(db: psycopg.Connection) -> None:
    client = build_client(db)
    page = client.get("/test/agronomist-only?x=1", headers={"accept": "text/html"})
    assert page.status_code == 303
    assert page.headers["location"] == "/login?next=%2Ftest%2Fagronomist-only%3Fx%3D1"
    htmx = client.get("/", headers={"HX-Request": "true"})
    assert htmx.status_code == 401 and htmx.headers["HX-Redirect"] == "/login"
    assert client.get("/").status_code == 401  # non-browser client


def test_logout_revokes_session(db: psycopg.Connection, org_a: Org, agronomist: str) -> None:
    client = build_client(db)
    login(client, agronomist)
    token = client.cookies["cp_session"]
    response = client.post("/logout", data={"csrf_token": page_csrf(client)})
    assert response.status_code == 303 and response.headers["location"] == "/login"
    row = db.execute(
        "select revoked_at from user_session where token_sha256 = %s",
        (security.token_sha256(token),),
    ).fetchone()
    assert row is not None and row[0] is not None
    # Replaying the old cookie does not work.
    replay = build_client(db)
    replay.cookies.set("cp_session", token, domain="testserver")
    assert replay.get("/").status_code == 401


def test_csrf_required_on_every_post(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(db)
    login(client, agronomist)
    token = page_csrf(client)
    assert client.post("/logout").status_code == 403
    assert client.post("/logout", data={"csrf_token": "0" * 64}).status_code == 403
    assert client.post("/logout", headers={"X-CSRF-Token": "bad"}).status_code == 403
    assert client.get("/").status_code == 200  # still signed in
    # HTMX variant: header token.
    htmx = client.post("/logout", headers={"X-CSRF-Token": token, "HX-Request": "true"})
    assert htmx.status_code == 204 and htmx.headers["HX-Redirect"] == "/login"


def test_csrf_token_is_per_session(db: psycopg.Connection, agronomist: str) -> None:
    first = build_client(db)
    login(first, agronomist)
    second = build_client(db)
    login(second, agronomist)
    assert first.post("/logout", data={"csrf_token": page_csrf(second)}).status_code == 403


def test_login_post_needs_login_csrf(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(db)
    login_csrf(client)
    response = client.post("/login", data={"email": agronomist, "password": PASSWORD})
    assert response.status_code == 403
    assert "This form expired" in response.text
    assert "cp_session" not in client.cookies


def test_disabled_user_cannot_log_in_and_loses_sessions(
    db: psycopg.Connection, org_a: Org, agronomist: str
) -> None:
    signed_in = build_client(db)
    login(signed_in, agronomist)
    db.execute("update app_user set disabled_at = now() where id = %s", (org_a.agronomist,))
    response = login(build_client(db), agronomist)
    assert response.status_code == 401 and GENERIC_ERROR in response.text
    assert signed_in.get("/").status_code == 401


def test_role_check_403(db: psycopg.Connection, org_a: Org) -> None:
    with_password(db, org_a.staff)
    staff = build_client(db)
    login(staff, email_of(db, org_a.staff))
    assert staff.get("/").status_code == 200  # staff may use the tool
    denied = staff.get("/test/agronomist-only", headers={"accept": "text/html"})
    assert denied.status_code == 403 and "agronomist" in denied.text

    with_password(db, org_a.agronomist)
    agro = build_client(db)
    login(agro, email_of(db, org_a.agronomist))
    assert agro.get("/test/agronomist-only").json() == {"org": str(org_a.id)}


def test_farmer_role_cannot_use_internal_tool(db: psycopg.Connection, org_a: Org) -> None:
    portal = insert(db, "app_user", email="portal@example.org", display_name="Portal")
    insert(db, "membership", organisation_id=org_a.id, user_id=portal, role="farmer")
    with_password(db, portal)
    client = build_client(db)
    login(client, "portal@example.org")
    assert client.get("/").status_code == 403


def test_user_in_two_orgs_chooses_one(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    insert(db, "membership", organisation_id=org_b.id, user_id=org_a.agronomist, role="agronomist")
    with_password(db, org_a.agronomist)
    client = build_client(db)
    login(client, email_of(db, org_a.agronomist))
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 303 and response.headers["location"] == "/orgs/choose"

    chooser = client.get("/orgs/choose")
    assert "Test org a" in chooser.text and "Test org b" in chooser.text
    token = page_csrf(client, "/orgs/choose")
    chosen = client.post("/orgs/choose", data={"org_id": str(org_b.id), "csrf_token": token})
    assert chosen.status_code == 303
    home = client.get("/")
    assert "Farmer b" in home.text and "Farmer a" not in home.text

    # Cannot pick an organisation you are not a member of.
    stranger = insert(db, "organisation", name="Stranger org")
    denied = client.post("/orgs/choose", data={"org_id": str(stranger), "csrf_token": token})
    assert denied.status_code == 403


def test_forged_org_cookie_is_ignored(db: psycopg.Connection, org_a: Org, org_b: Org) -> None:
    insert(db, "membership", organisation_id=org_b.id, user_id=org_a.agronomist, role="staff")
    with_password(db, org_a.agronomist)
    client = build_client(db)
    login(client, email_of(db, org_a.agronomist))
    client.cookies.set("cp_org", f"{org_b.id}.{'0' * 64}", domain="testserver")
    assert client.get("/", headers={"accept": "text/html"}).headers["location"] == "/orgs/choose"
