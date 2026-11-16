"""S4 (security review S2-auth-review-step5): the role check against a real Postgres."""

from __future__ import annotations

import psycopg
import pytest

from cloverproof_app.config import ConfigError
from cloverproof_app.db.pool import check_least_privilege

from .conftest import as_owner, as_role

pytestmark = pytest.mark.db


def test_cp_app_passes(db: psycopg.Connection) -> None:
    check_least_privilege(db)  # the fixture runs as cp_app


def test_cp_admin_is_refused(db: psycopg.Connection) -> None:
    # cp_admin is a member of cp_app but may write memberships: CLI only (ADR 0006).
    with as_role(db, "cp_admin"), pytest.raises(ConfigError, match="cp_admin"):
        check_least_privilege(db)


def test_superuser_is_refused(db: psycopg.Connection) -> None:
    with as_owner(db), pytest.raises(ConfigError, match="superuser"):
        check_least_privilege(db)


def test_role_outside_cp_app_is_refused(db: psycopg.Connection) -> None:
    with as_role(db, "cp_website"), pytest.raises(ConfigError, match="cp_app"):
        check_least_privilege(db)
