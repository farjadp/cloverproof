"""Review queue and engine-vs-final diff queries (read-only).

Every function takes `org_id` and filters every joined table by it. Nothing here writes.

Status of a plan = review state of its latest version (the leaf of the parent_id chain):
`approved` / `rejected` only when a HUMAN final review exists (`agronomist_approved` or
`superadmin_approved`, CLAUDE.md rule 8); otherwise `awaiting`. An `ai_reviewed` review
(rule 11) never ends the wait: it is reported as a separate flag.

TODO(cp-database): switch the status computation to the `recommendation_state` view once
its migration lands (S2-DB, RK-X4); the queue should read only that view.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import class_row

from cloverproof_app.repo.farms import like_pattern

HUMAN_REVIEW_KINDS = ("agronomist_approved", "superadmin_approved")


@dataclass(frozen=True)
class QueueRow:
    plan_id: UUID
    recommendation_id: UUID
    farmer_name: str
    farm_name: str
    field_name: str
    crop: str
    season_label: str
    plan_date: Any
    plan_created_at: datetime
    version_created_at: datetime
    version_kind: str  # engine | agronomist
    version_number: int
    confidence: str
    placeholder_pack: bool
    uses_placeholder: bool
    ai_reviewed: bool
    status: str  # awaiting | approved | rejected
    total: int  # rows matching the filters (before the limit)


@dataclass(frozen=True)
class QueueQuery:
    """Already-validated filter values (see cloverproof_app.review_queue.parse_filters)."""

    status: str = "awaiting"  # awaiting | approved | rejected | all
    confidence: str = "any"  # any | low | medium | high
    crop: str = "any"
    ai: str = "any"  # any | yes | no
    sort: str = "oldest"  # oldest | newest | farmer | confidence
    q: str = ""


# Fixed SQL fragments chosen by whitelisted keys; user values only ever go in as params.
_ORDER = {
    "oldest": "version_created_at asc, plan_id",
    "newest": "version_created_at desc, plan_id",
    "farmer": "lower(farmer_name), lower(field_name), version_created_at asc, plan_id",
    "confidence": (
        "case confidence when 'low' then 0 when 'medium' then 1 else 2 end,"
        " version_created_at asc, plan_id"
    ),
}

_BASE = """
select p.id as plan_id, l.id as recommendation_id,
  fr.display_name as farmer_name, fa.name as farm_name, f.name as field_name,
  p.crop, s.label as season_label, p.plan_date, p.created_at as plan_created_at,
  l.created_at as version_created_at, l.kind::text as version_kind,
  (select count(*) from recommendation r2
    where r2.organisation_id = p.organisation_id and r2.crop_plan_id = p.id)::int
    as version_number,
  l.confidence::text as confidence,
  l.pack_status = 'placeholder' as placeholder_pack,
  (jsonb_path_exists(l.result, '$.** ? (@.uses_placeholder == true)')
    or jsonb_path_exists(l.result, '$.**.constants_used[*] ? (@.status == "PLACEHOLDER")'))
    as uses_placeholder,
  exists (select 1 from review a where a.organisation_id = p.organisation_id
    and a.recommendation_id = l.id and a.review_kind = 'ai_reviewed') as ai_reviewed,
  case fin.decision when 'approve' then 'approved' when 'reject' then 'rejected'
    else 'awaiting' end as status
from crop_plan p
join season s on s.organisation_id = p.organisation_id and s.id = p.season_id
join field f on f.organisation_id = p.organisation_id and f.id = p.field_id
join farm fa on fa.organisation_id = p.organisation_id and fa.id = f.farm_id
join farmer fr on fr.organisation_id = p.organisation_id and fr.id = fa.farmer_id
join lateral (
  select r.id, r.kind, r.confidence, r.pack_status, r.result, r.created_at
  from recommendation r
  where r.organisation_id = p.organisation_id and r.crop_plan_id = p.id
    and not exists (select 1 from recommendation c
      where c.organisation_id = r.organisation_id and c.parent_id = r.id)
  order by r.created_at desc, r.id desc limit 1
) l on true
left join lateral (
  select v.decision::text as decision from review v
  where v.organisation_id = p.organisation_id and v.recommendation_id = l.id
    and v.review_kind = any(%(human)s) and v.decision in ('approve', 'reject')
  order by v.created_at limit 1
) fin on true
where p.organisation_id = %(org)s
"""


def queue(conn: psycopg.Connection, org_id: UUID, query: QueueQuery, *,
          limit: int) -> list[QueueRow]:  # fmt: skip
    """Latest version of every crop plan in the org, filtered and sorted."""
    where: list[str] = []
    params: dict[str, Any] = {"org": org_id, "human": list(HUMAN_REVIEW_KINDS), "limit": limit}
    if query.status != "all":
        where.append("status = %(status)s")
        params["status"] = query.status
    if query.confidence != "any":
        where.append("confidence = %(confidence)s")
        params["confidence"] = query.confidence
    if query.crop != "any":
        where.append("crop = %(crop)s")
        params["crop"] = query.crop
    if query.ai == "yes":
        where.append("ai_reviewed")
    elif query.ai == "no":
        where.append("not ai_reviewed")
    if query.q.strip():
        where.append(
            "(lower(farmer_name) like %(q)s or lower(farm_name) like %(q)s"
            " or lower(field_name) like %(q)s)"
        )
        params["q"] = like_pattern(query.q)
    sql = (
        "select *, count(*) over ()::int as total from (" + _BASE + ") q"
        + (" where " + " and ".join(where) if where else "")
        + " order by " + _ORDER.get(query.sort, _ORDER["oldest"])
        + " limit %(limit)s"
    )  # fmt: skip
    with conn.cursor(row_factory=class_row(QueueRow)) as cur:
        return cur.execute(sql, params).fetchall()  # type: ignore[arg-type]


def crops(conn: psycopg.Connection, org_id: UUID) -> list[str]:
    """Distinct crops of the org's plans (for the Crop filter)."""
    rows = conn.execute(
        "select distinct crop from crop_plan where organisation_id = %s order by crop", (org_id,)
    ).fetchall()
    return [r[0] for r in rows]


@dataclass(frozen=True)
class EditStep:
    number: int  # version number in the chain (engine = 1)
    recommendation_id: UUID
    author: str
    reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class DiffSource:
    engine_recommendation_id: UUID
    final_recommendation_id: UUID
    edit_depth: int
    engine_result: dict[str, Any]
    final_result: dict[str, Any]
    edits: list[EditStep]  # every edit from the engine to this version, oldest first


def diff_source(conn: psycopg.Connection, org_id: UUID, final_id: UUID) -> DiffSource | None:
    """Engine root vs `final_id`, from the recommendation_diff view (unchanged), plus the
    reason of every edit on the way."""
    row = conn.execute(
        "select engine_recommendation_id, final_recommendation_id, edit_depth,"
        " engine_result, final_result from recommendation_diff"
        " where organisation_id = %s and final_recommendation_id = %s",
        (org_id, final_id),
    ).fetchone()
    if row is None:
        return None
    engine_id, final_rec, depth, engine_result, final_result = row
    steps = conn.execute(
        "with recursive chain as ("
        "  select r.id, r.parent_id, 0 as up from recommendation r"
        "  where r.organisation_id = %(org)s and r.id = %(id)s"
        "  union all"
        "  select r.id, r.parent_id, c.up + 1 from recommendation r"
        "  join chain c on r.id = c.parent_id where r.organisation_id = %(org)s"
        ") select r.id, c.up, u.display_name, r.reason, r.created_at from chain c"
        " join recommendation r on r.organisation_id = %(org)s and r.id = c.id"
        " join app_user u on u.id = r.created_by"
        " where r.parent_id is not null order by c.up desc",
        {"org": org_id, "id": final_id},
    ).fetchall()
    edits = [
        EditStep(
            number=depth - up + 1,
            recommendation_id=rid,
            author=author,
            reason=reason,
            created_at=created,
        )
        for rid, up, author, reason, created in steps
    ]
    return DiffSource(engine_id, final_rec, depth, engine_result, final_result, edits)
