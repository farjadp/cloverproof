"""App side of the S2 delta review (PR #7): B1, F1, F2, F4, N11, N13, N15 (real database)."""

from __future__ import annotations

import psycopg
import pytest

from .conftest import Org, insert
from .test_plan_flow import signed_in
from .test_web_auth import PASSWORD, build_client, email_of, login, page_csrf

pytestmark = pytest.mark.db


def test_search_wildcards_match_literally(db: psycopg.Connection, org_a: Org) -> None:
    insert(db, "farmer", organisation_id=org_a.id, display_name="Field_50% Ltd")
    client, _ = signed_in(db, org_a.agronomist)
    assert "Farmer a" in client.get("/farmers", params={"q": ""}).text
    assert "Farmer a" not in client.get("/farmers", params={"q": "%"}).text
    assert "Farmer a" not in client.get("/farmers", params={"q": "_"}).text
    assert "Field_50% Ltd" in client.get("/farmers", params={"q": "_50%"}).text


def test_wrong_current_password_does_not_lock_sign_in(db: psycopg.Connection, org_a: Org) -> None:
    client, csrf = signed_in(db, org_a.agronomist)
    client.post("/logout", data={"csrf_token": csrf})
    c = build_client(db, login_max_failures=2)
    email = email_of(db, org_a.agronomist)
    assert login(c, email).status_code == 303
    token = page_csrf(c, "/account/password")
    for _ in range(2):
        r = c.post(
            "/account/password",
            data={"csrf_token": token, "current_password": "wrong password!!",
                  "new_password": "x" * 20, "confirm_password": "x" * 20},
        )  # fmt: skip
        assert r.status_code == 422
    c.post("/logout", data={"csrf_token": token})
    assert login(c, email, PASSWORD).status_code == 303
