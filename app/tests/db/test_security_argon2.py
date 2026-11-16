"""S2 (security review S2-auth-review-step5): argon2 slots and global failure budget."""

from __future__ import annotations

import psycopg
import pytest

from cloverproof_app import security

from .conftest import Org
from .test_web_auth import build_client, email_of, login, with_password

pytestmark = pytest.mark.db

WRONG = "not the right password"


@pytest.fixture
def agronomist(db: psycopg.Connection, org_a: Org) -> str:
    with_password(db, org_a.agronomist)
    return email_of(db, org_a.agronomist)


def test_global_failure_budget_returns_503(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(
        db,
        login_global_max_failures_per_minute=2,
        login_ip_max_failures=100,
        login_max_failures=100,
    )
    for i in range(2):
        assert login(client, f"x{i}@example.org", WRONG).status_code == 401
    response = login(client, agronomist)
    assert response.status_code == 503 and "cp_session" not in client.cookies


def test_argon2_slot_timeout_returns_503(db: psycopg.Connection, agronomist: str) -> None:
    client = build_client(db, argon2_max_concurrency=1, argon2_acquire_timeout_seconds=1)
    # Hold the only slot, as a concurrent login would.
    held = security.hash_slots()
    assert held.acquire(timeout=1)
    try:
        response = login(client, agronomist)
    finally:
        held.release()
    assert response.status_code == 503 and "try again" in response.text.lower()
    assert login(client, agronomist).status_code == 303
