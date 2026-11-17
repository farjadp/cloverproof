"""F4: minutes per review = since the previous review on the plan (or since open), capped."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from cloverproof_app import plan_web
from cloverproof_app.auth import CurrentUser, OrgContext
from cloverproof_app.config import ConfigError, Settings
from cloverproof_app.repo.users import Organisation
from cloverproof_app.timer import review_minutes

NOW = 1_800_000_000
BASE = {"DATABASE_URL": "postgresql://u@localhost/db", "SESSION_SECRET": "s" * 40}


def at(seconds_ago: int) -> datetime:
    return datetime.fromtimestamp(NOW - seconds_ago, UTC)


def test_minutes_since_open_without_previous_review() -> None:
    m = review_minutes(NOW - 450, None, cap=240, now=NOW)
    assert (m.minutes, m.capped, m.started_at) == (7, False, at(450))


def test_minutes_since_previous_review_when_later_than_open() -> None:
    # Opened 15 min ago, edited 5 min ago: this review counts 5, not 15 (no double count).
    m = review_minutes(NOW - 900, at(300), cap=240, now=NOW)
    assert (m.minutes, m.started_at) == (5, at(300))


def test_open_after_previous_review_counts_from_open() -> None:
    m = review_minutes(NOW - 120, at(3600), cap=240, now=NOW)
    assert (m.minutes, m.started_at) == (2, at(120))


def test_minutes_are_capped_and_flagged() -> None:
    m = review_minutes(NOW - 5 * 3600, None, cap=240, now=NOW)
    assert (m.minutes, m.capped, m.measured) == (240, True, 300)


def test_cap_is_not_flagged_at_exactly_the_cap() -> None:
    m = review_minutes(NOW - 240 * 60, None, cap=240, now=NOW)
    assert (m.minutes, m.capped) == (240, False)


def test_cap_setting_default_and_env() -> None:
    assert Settings.from_env(BASE).review_minutes_cap == 240
    assert Settings.from_env({**BASE, "REVIEW_MINUTES_CAP": "90"}).review_minutes_cap == 90
    with pytest.raises(ConfigError, match="REVIEW_MINUTES_CAP"):
        Settings.from_env({**BASE, "REVIEW_MINUTES_CAP": "0"})


def context(kind: str, roles: tuple[str, ...], platform_role: str | None = None) -> OrgContext:
    user = CurrentUser(
        uuid4(), "a@example.org", "A", uuid4(), "h", actor_kind=kind, platform_role=platform_role
    )
    org = Organisation(uuid4(), "Org")
    return OrgContext(user, org, roles, (org,))


def test_only_a_human_agronomist_or_superadmin_may_review() -> None:
    allowed = [
        context("human", ("agronomist",)),
        context("human", ("staff",), "superadmin"),
        context("human", ("agronomist",), "superadmin"),
    ]
    for ctx in allowed:
        plan_web.require_agronomist(ctx)
        assert plan_web.is_agronomist(ctx)
    denied = [
        context("service", ("agronomist",)),
        context("service", ("staff",), "superadmin"),
        context("service", ("agronomist",), "superadmin"),
        context("human", ("staff",)),
        context("human", ("owner",)),
    ]
    for ctx in denied:
        with pytest.raises(HTTPException) as error:
            plan_web.require_agronomist(ctx)
        assert error.value.status_code == 403
        assert not plan_web.is_agronomist(ctx)


def test_review_kind_follows_actor_and_role() -> None:
    kind = plan_web.review_kind_for
    assert kind(context("human", ("agronomist",))) == "agronomist_approved"
    assert kind(context("human", ("agronomist",), "superadmin")) == "agronomist_approved"
    assert kind(context("human", ("staff",), "superadmin")) == "superadmin_approved"
    assert kind(context("service", ("agronomist",), "superadmin")) == "ai_reviewed"
    with pytest.raises(ValueError, match="not a reviewer"):
        kind(context("human", ("staff",)))
    with pytest.raises(ValueError, match="actor_kind"):
        kind(context("robot", ("agronomist",)))
