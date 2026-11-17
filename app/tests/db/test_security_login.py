"""S1/S2 (security review S2-auth-review-step5): login limits end to end, real database."""

from __future__ import annotations

import logging

import psycopg
import pytest

from cloverproof_app import cli
from cloverproof_app.ratelimit import LoginDecision, LoginGuard, UnlockListener, account_key

from .conftest import MigratedDb, Org
from .test_web_auth import PASSWORD, build_client, email_of, login, login_csrf, with_password

pytestmark = pytest.mark.db

WRONG = "not the right password"


@pytest.fixture
def agronomist(db: psycopg.Connection, org_a: Org) -> str:
    with_password(db, org_a.agronomist)
    return email_of(db, org_a.agronomist)


def test_spoofed_x_forwarded_for_does_not_reset_ip_counter(
    db: psycopg.Connection, agronomist: str
) -> None:
    client = build_client(db, login_ip_max_failures=3, login_max_failures=100)
    for i in range(3):
        token = login_csrf(client)
        response = client.post(
            "/login",
            data={"email": f"guess{i}@example.org", "password": WRONG, "csrf_token": token},
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        )
        assert response.status_code == 401
    token = login_csrf(client)
    blocked = client.post(
        "/login",
        data={"email": agronomist, "password": PASSWORD, "csrf_token": token},
        headers={"X-Forwarded-For": "10.9.9.9"},
    )
    assert blocked.status_code == 429 and "Too many attempts" in blocked.text
    assert "cp_session" not in client.cookies


def test_trusted_header_keys_the_counter_and_x_forwarded_for_is_ignored(
    db: psycopg.Connection, agronomist: str
) -> None:
    client = build_client(
        db, login_ip_max_failures=2, login_max_failures=100, trusted_proxy_header="X-Real-IP"
    )
    for i in range(2):
        token = login_csrf(client)
        client.post(
            "/login",
            data={"email": f"g{i}@example.org", "password": WRONG, "csrf_token": token},
            headers={"X-Real-IP": "198.51.100.7", "X-Forwarded-For": f"10.0.0.{i}"},
        )
    token = login_csrf(client)
    same_ip = client.post(
        "/login",
        data={"email": agronomist, "password": PASSWORD, "csrf_token": token},
        headers={"X-Real-IP": "198.51.100.7", "X-Forwarded-For": "1.1.1.1"},
    )
    assert same_ip.status_code == 429
    token = login_csrf(client)
    other_ip = client.post(
        "/login",
        data={"email": agronomist, "password": PASSWORD, "csrf_token": token},
        headers={"X-Real-IP": "198.51.100.8"},
    )
    assert other_ip.status_code == 303


def test_account_soft_limit_pauses_even_the_right_password(
    db: psycopg.Connection, agronomist: str, caplog: pytest.LogCaptureFixture
) -> None:
    client = build_client(
        db, login_account_max_failures=3, login_ip_max_failures=100, login_max_failures=100
    )
    for i in range(3):
        token = login_csrf(client)
        client.post(
            "/login",
            data={"email": agronomist, "password": WRONG, "csrf_token": token},
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        )
    with caplog.at_level(logging.WARNING):
        paused = login(client, agronomist)
    assert paused.status_code == 503
    assert "try again later" in paused.text.lower()
    assert "cp_session" not in client.cookies
    assert any("paused" in r.getMessage() for r in caplog.records)
    assert not any(agronomist in r.getMessage() for r in caplog.records)  # no PII in logs

    # Unlock (what `cli user-unlock` triggers through the listener) lets the user in.
    client.app.state.login_guard.unlock_account(account_key(agronomist))  # type: ignore[attr-defined]
    assert login(client, agronomist).status_code == 303


def test_cli_user_unlock_reaches_the_running_app(migrated_db: MigratedDb) -> None:
    guard = LoginGuard(
        pair_max=100,
        pair_window=900,
        ip_max=100,
        ip_window=900,
        account_max=1,
        account_window=3600,
        global_max=100,
    )
    listener = UnlockListener(migrated_db.url)
    guard.unlock_listener = listener
    listener.open()
    try:
        guard.record_failure("farjad@example.org", "ip")
        guard.record_failure("other@example.org", "ip")
        assert guard.check("farjad@example.org", "ip2") is LoginDecision.ACCOUNT_PAUSED

        with psycopg.connect(migrated_db.url) as conn:  # what `cli user-unlock` runs
            cli.user_unlock(conn, email=" Farjad@Example.org")

        assert guard.check("farjad@example.org", "ip2") is LoginDecision.OK
        assert guard.check("other@example.org", "ip2") is LoginDecision.ACCOUNT_PAUSED
    finally:
        listener.close()


def test_cli_user_unlock_command(
    migrated_db: MigratedDb, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", migrated_db.url)
    assert cli.main(["user-unlock", "--email", "farjad@example.org"]) == 0
    out = capsys.readouterr().out
    assert "unlock sent" in out


def test_oversized_login_input_rerenders_login_page_without_echo(
    db: psycopg.Connection, agronomist: str
) -> None:
    client = build_client(db)
    token = login_csrf(client)
    secret = "p" * 2000
    response = client.post(
        "/login", data={"email": agronomist, "password": secret, "csrf_token": token}
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")
    assert "Email or password is incorrect" in response.text
    assert secret not in response.text
    assert 'name="csrf_token"' in response.text  # a usable form again
