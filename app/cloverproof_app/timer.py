"""Minutes-per-plan timer (the internal tool's key metric).

The start time is a server timestamp signed with SESSION_SECRET and bound to the session
and the plan, so it cannot be edited in the browser without detection:
- the New plan form carries a signed start in a hidden field (data entry counts);
- once the plan exists the start lives in an HttpOnly cookie scoped to /plans/{id};
- a plan opened without a valid start begins counting at that moment.
`minutes_spent` (security review F4) = whole minutes from the later of that start and the
previous review on the plan, to this review's submit, computed on the server and capped at
REVIEW_MINUTES_CAP. Summing minutes over a plan's reviews gives the time spent on it once.
After an edit the start is reset to now; after approve/reject the cookie is deleted (N14).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from fastapi.responses import Response

from cloverproof_app import security
from cloverproof_app.auth import CurrentUser
from cloverproof_app.config import Settings

MAX_AGE = 7 * 24 * 3600


def cookie_name(plan_id: UUID) -> str:
    return f"cp_timer_{plan_id.hex}"


def _signed(settings: Settings, purpose: str, started: int) -> str:
    return f"{started}.{security.sign(settings.session_secret, purpose, str(started))}"


def _read(settings: Settings, purpose: str, raw: str | None) -> int | None:
    stamp, _, signature = (raw or "").partition(".")
    if not stamp.isdigit():
        return None
    expected = security.sign(settings.session_secret, purpose, stamp)
    started = int(stamp)
    if not security.same(signature, expected) or started > time.time() + 5:
        return None
    return started


def _plan_purpose(user: CurrentUser, plan_id: UUID) -> str:
    return f"timer:{user.session_id}:{plan_id}"


def _form_purpose(user: CurrentUser, field_id: UUID) -> str:
    return f"timer-new:{user.session_id}:{field_id}"


def new_form_token(settings: Settings, user: CurrentUser, field_id: UUID) -> str:
    return _signed(settings, _form_purpose(user, field_id), int(time.time()))


def form_start(settings: Settings, user: CurrentUser, field_id: UUID, raw: str | None) -> int:
    started = _read(settings, _form_purpose(user, field_id), raw)
    return started if started is not None else int(time.time())


def plan_start(
    request: Request, settings: Settings, user: CurrentUser, plan_id: UUID
) -> int | None:
    raw = request.cookies.get(cookie_name(plan_id))
    return _read(settings, _plan_purpose(user, plan_id), raw)


def set_plan_start(response: Response, settings: Settings, user: CurrentUser, plan_id: UUID,
                   started: int) -> None:  # fmt: skip
    response.set_cookie(
        cookie_name(plan_id),
        _signed(settings, _plan_purpose(user, plan_id), started),
        max_age=MAX_AGE,
        path=f"/plans/{plan_id}",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def clear_plan_start(response: Response, settings: Settings, plan_id: UUID) -> None:
    response.delete_cookie(
        cookie_name(plan_id),
        path=f"/plans/{plan_id}",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@dataclass(frozen=True)
class ReviewMinutes:
    minutes: int  # stored in review.minutes_spent (capped)
    measured: int  # before the cap
    capped: bool
    started_at: datetime  # stored in review.started_at


def review_minutes(
    started: int, previous_review_at: datetime | None, *, cap: int, now: float | None = None
) -> ReviewMinutes:
    """Minutes for one review: from the signed start or the previous review, whichever is later."""
    start = float(started)
    if previous_review_at is not None:
        start = max(start, previous_review_at.timestamp())
    now = time.time() if now is None else now
    measured = max(0, int(now - start) // 60)
    return ReviewMinutes(
        minutes=min(measured, cap),
        measured=measured,
        capped=measured > cap,
        started_at=datetime.fromtimestamp(start, UTC),
    )


def minutes_since(started: int) -> int:
    return max(0, int(time.time() - started) // 60)
