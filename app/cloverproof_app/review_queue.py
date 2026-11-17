"""Review queue (`/review`) and the engine-vs-final line diff shown on the plan page.

Read-only: nothing here writes, and the approval flow (plan_web.plan_review) is unchanged.
Who may see the queue: the same rule as who may review (plan_web.is_agronomist: a human
agronomist of the org, or a human superadmin member of it). Everyone else gets 403.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from cloverproof_app import planning
from cloverproof_app.auth import Conn
from cloverproof_app.plan_web import STATUS_LABELS, InternalOrg, require_agronomist
from cloverproof_app.repo import review_queue as repo
from cloverproof_app.web import render

router = APIRouter()

# Hard cap per page (spec §3.6: no pagination in S2; expected volume is 5-10 farms).
# TODO(cp-concierge-app): read REVIEW_QUEUE_LIMIT from Settings once .env.example has it.
QUEUE_LIMIT = 200
Q_MAX = 100

STATUS_OPTIONS = {
    "awaiting": "Awaiting decision",
    "approved": "Approved",
    "rejected": "Rejected",
    "all": "All",
}
CONFIDENCE_OPTIONS = {"any": "Any", "low": "Low", "medium": "Medium", "high": "High"}
AI_OPTIONS = {"any": "Any", "yes": "AI review present", "no": "No AI review"}
SORT_OPTIONS = {
    "oldest": "Waiting longest first",
    "newest": "Newest first",
    "farmer": "Farmer name, A to Z",
    "confidence": "Lowest confidence first",
}
DEFAULTS = {"status": "awaiting", "confidence": "any", "crop": "any", "ai": "any",
            "sort": "oldest", "q": ""}  # fmt: skip
ROW_STATUS = {"awaiting": "in_review", "approved": "approved", "rejected": "rejected"}


def parse_filters(params: Mapping[str, str], crops: list[str]) -> repo.QueueQuery:
    """Query params -> filter values. Unknown or invalid values fall back to the default
    silently (spec §3.5); the raw value is never echoed."""

    def pick(name: str, allowed: Mapping[str, Any] | list[str]) -> str:
        value = params.get(name, DEFAULTS[name])
        return value if value in allowed else DEFAULTS[name]

    return repo.QueueQuery(
        status=pick("status", STATUS_OPTIONS),
        confidence=pick("confidence", CONFIDENCE_OPTIONS),
        crop=pick("crop", ["any", *crops]),
        ai=pick("ai", AI_OPTIONS),
        sort=pick("sort", SORT_OPTIONS),
        q=(params.get("q") or "").strip()[:Q_MAX],
    )


def active_filters(query: repo.QueueQuery) -> int:
    return sum(
        1 for name in ("status", "confidence", "crop", "ai", "q")
        if getattr(query, name) != DEFAULTS[name]
    )  # fmt: skip


@router.get("/review")
def review_queue(request: Request, conn: Conn, context: InternalOrg) -> Response:
    require_agronomist(context)
    org = context.org.id
    crops = repo.crops(conn, org)
    query = parse_filters(request.query_params, crops)
    rows = repo.queue(conn, org, query, limit=QUEUE_LIMIT)
    total = rows[0].total if rows else 0
    ctx = {
        "rows": rows,
        "total": total,
        "shown": len(rows),
        "f": query,
        "active": active_filters(query),
        "crops": crops,
        "crop_labels": planning.CROP_LABELS,
        "status_options": STATUS_OPTIONS,
        "confidence_options": CONFIDENCE_OPTIONS,
        "ai_options": AI_OPTIONS,
        "sort_options": SORT_OPTIONS,
        "row_status": ROW_STATUS,
        "status_labels": STATUS_LABELS,
    }
    name = "_review_rows.html" if request.headers.get("HX-Request") else "review_queue.html"
    return render(request, name, ctx)
