"""Soil tests, crop plans, recommendations (insert-only) and reviews (insert-only).

Every function takes `org_id` and filters by it. Recommendations and reviews are never
updated: an edit is a new recommendation row with parent_id + reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import class_row
from psycopg.types.json import Jsonb

from cloverproof_engine.models import SoilTest


@dataclass(frozen=True)
class SoilTestRow:
    id: UUID
    sample_date: date
    depth_top_cm: Decimal
    depth_bottom_cm: Decimal
    source: str
    lab: str | None


@dataclass(frozen=True)
class SoilValueRow:
    form: str
    value: Decimal
    unit: str
    extraction_method: str
    extraction_method_detail: str | None


@dataclass(frozen=True)
class PlanRow:
    id: UUID
    field_id: UUID
    season_label: str
    crop: str
    target_yield_t_ha: Decimal
    previous_crop: str
    plan_date: date
    soil_test_id: UUID | None
    created_at: datetime


@dataclass(frozen=True)
class RecRow:
    id: UUID
    parent_id: UUID | None
    kind: str
    reason: str | None
    result: dict[str, Any]
    confidence: str
    created_by_name: str
    created_at: datetime


@dataclass(frozen=True)
class ReviewRow:
    id: UUID
    recommendation_id: UUID
    decision: str
    review_kind: str  # agronomist_approved | ai_reviewed (CLAUDE.md rule 11)
    reason: str | None
    reviewer_name: str
    minutes_spent: int
    resulting_recommendation_id: UUID | None
    created_at: datetime


@dataclass(frozen=True)
class PlanSummary:
    id: UUID
    season_label: str
    crop: str
    plan_date: date
    versions: int
    confidence: str | None
    status: str
    updated_at: datetime


def latest_soil_test(conn: psycopg.Connection, org_id: UUID, field_id: UUID) -> SoilTestRow | None:
    with conn.cursor(row_factory=class_row(SoilTestRow)) as cur:
        return cur.execute(
            "select id, sample_date, depth_top_cm, depth_bottom_cm, source::text, lab"
            " from soil_test where organisation_id = %s and field_id = %s"
            " order by sample_date desc, created_at desc limit 1",
            (org_id, field_id),
        ).fetchone()


def get_soil_test(conn: psycopg.Connection, org_id: UUID, soil_test_id: UUID) -> SoilTestRow | None:
    with conn.cursor(row_factory=class_row(SoilTestRow)) as cur:
        return cur.execute(
            "select id, sample_date, depth_top_cm, depth_bottom_cm, source::text, lab"
            " from soil_test where organisation_id = %s and id = %s",
            (org_id, soil_test_id),
        ).fetchone()


def soil_test_values(conn: psycopg.Connection, org_id: UUID,
                     soil_test_id: UUID) -> list[SoilValueRow]:  # fmt: skip
    with conn.cursor(row_factory=class_row(SoilValueRow)) as cur:
        return cur.execute(
            "select form::text, value, unit::text, extraction_method::text,"
            " extraction_method_detail from soil_test_value"
            " where organisation_id = %s and soil_test_id = %s order by nutrient, form",
            (org_id, soil_test_id),
        ).fetchall()


def create_soil_test(conn: psycopg.Connection, org_id: UUID, *, field_id: UUID, soil: SoilTest,
                     user_id: UUID) -> UUID:  # fmt: skip
    row = conn.execute(
        "insert into soil_test (organisation_id, field_id, sample_date, depth_top_cm,"
        " depth_bottom_cm, source, lab, created_by) values (%s, %s, %s, %s, %s, %s, %s, %s)"
        " returning id",
        (org_id, field_id, soil.sample_date, soil.depth_top_cm, soil.depth_bottom_cm,
         soil.source.value, soil.lab, user_id),
    ).fetchone()  # fmt: skip
    assert row is not None
    test_id: UUID = row[0]
    for v in soil.values:
        conn.execute(
            "insert into soil_test_value (organisation_id, soil_test_id, form, value, unit,"
            " extraction_method, extraction_method_detail) values (%s, %s, %s, %s, %s, %s, %s)",
            (org_id, test_id, v.form.value, v.value, v.unit.value, v.extraction_method.value,
             v.extraction_method_detail),
        )  # fmt: skip
    return test_id


def create_crop_plan(conn: psycopg.Connection, org_id: UUID, *, field_id: UUID, season_id: UUID,
                     crop: str, target_yield_t_ha: float, previous_crop: str, plan_date: date,
                     soil_test_id: UUID | None, user_id: UUID) -> UUID:  # fmt: skip
    row = conn.execute(
        "insert into crop_plan (organisation_id, field_id, season_id, crop, target_yield_t_ha,"
        " previous_crop, plan_date, soil_test_id, created_by)"
        " values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
        (org_id, field_id, season_id, crop, target_yield_t_ha, previous_crop, plan_date,
         soil_test_id, user_id),
    ).fetchone()  # fmt: skip
    assert row is not None
    return row[0]


def get_plan(conn: psycopg.Connection, org_id: UUID, plan_id: UUID) -> PlanRow | None:
    with conn.cursor(row_factory=class_row(PlanRow)) as cur:
        return cur.execute(
            "select p.id, p.field_id, s.label as season_label, p.crop, p.target_yield_t_ha,"
            " p.previous_crop, p.plan_date, p.soil_test_id, p.created_at"
            " from crop_plan p join season s"
            "   on s.organisation_id = p.organisation_id and s.id = p.season_id"
            " where p.organisation_id = %s and p.id = %s",
            (org_id, plan_id),
        ).fetchone()


def lock_plan(conn: psycopg.Connection, org_id: UUID, plan_id: UUID) -> bool:
    """Row-lock the plan until commit (F1): edits and reviews of one plan run one at a time,
    so the version read after this is still the latest when the new row is inserted."""
    row = conn.execute(
        "select id from crop_plan where organisation_id = %s and id = %s for update",
        (org_id, plan_id),
    ).fetchone()
    return row is not None


def insert_recommendation(conn: psycopg.Connection, org_id: UUID, *, crop_plan_id: UUID,
                          result: dict[str, Any], user_id: UUID, parent_id: UUID | None = None,
                          reason: str | None = None) -> UUID:  # fmt: skip
    """INSERT only. Typed columns are copied from the document (CHECKs keep them equal)."""
    kind = "engine" if parent_id is None else "agronomist"
    row = conn.execute(
        "insert into recommendation (organisation_id, crop_plan_id, parent_id, kind, reason,"
        " inputs_snapshot, result, engine_version, pack_id, pack_version, pack_status,"
        " pack_sha256, confidence, created_by)"
        " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
        (org_id, crop_plan_id, parent_id, kind, reason, Jsonb(result["input_snapshot"]),
         Jsonb(result), result["engine_version"], result["pack_id"], result["pack_version"],
         result["pack_status"], result["pack_sha256"], result["confidence"], user_id),
    ).fetchone()  # fmt: skip
    assert row is not None
    return row[0]


def recommendations(conn: psycopg.Connection, org_id: UUID, plan_id: UUID) -> list[RecRow]:
    """All versions of a plan, oldest first (v1 = index 0)."""
    with conn.cursor(row_factory=class_row(RecRow)) as cur:
        return cur.execute(
            "select r.id, r.parent_id, r.kind::text, r.reason, r.result,"
            " r.confidence::text, u.display_name as created_by_name, r.created_at"
            " from recommendation r join app_user u on u.id = r.created_by"
            " where r.organisation_id = %s and r.crop_plan_id = %s"
            " order by r.created_at, r.id",
            (org_id, plan_id),
        ).fetchall()


def reviews(conn: psycopg.Connection, org_id: UUID, plan_id: UUID) -> list[ReviewRow]:
    with conn.cursor(row_factory=class_row(ReviewRow)) as cur:
        return cur.execute(
            "select v.id, v.recommendation_id, v.decision::text, v.review_kind, v.reason,"
            " u.display_name as reviewer_name, v.minutes_spent,"
            " v.resulting_recommendation_id, v.created_at"
            " from review v join recommendation r"
            "   on r.organisation_id = v.organisation_id and r.id = v.recommendation_id"
            " join app_user u on u.id = v.reviewer_id"
            " where v.organisation_id = %s and r.crop_plan_id = %s"
            " order by v.created_at, v.id",
            (org_id, plan_id),
        ).fetchall()


def insert_review(conn: psycopg.Connection, org_id: UUID, *, recommendation_id: UUID,
                  decision: str, review_kind: str, reason: str | None, reviewer_id: UUID,
                  minutes_spent: int, started_at: datetime | None = None,
                  resulting_recommendation_id: UUID | None = None) -> UUID:  # fmt: skip
    row = conn.execute(
        "insert into review (organisation_id, recommendation_id, decision, review_kind, reason,"
        " reviewer_id, minutes_spent, started_at, resulting_recommendation_id)"
        " values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
        (org_id, recommendation_id, decision, review_kind, reason, reviewer_id, minutes_spent,
         started_at, resulting_recommendation_id),
    ).fetchone()  # fmt: skip
    assert row is not None
    return row[0]


def diff_row(conn: psycopg.Connection, org_id: UUID, final_id: UUID) -> dict[str, Any] | None:
    """Engine root vs this version, from the recommendation_diff view."""
    cur = conn.execute(
        "select engine_recommendation_id, edit_depth, engine_n_rate_kg_ha, final_n_rate_kg_ha,"
        " n_rate_delta_kg_ha, edit_reason, engine_result, final_result"
        " from recommendation_diff where organisation_id = %s and final_recommendation_id = %s",
        (org_id, final_id),
    )
    row = cur.fetchone()
    if row is None:
        return None
    names = [c.name for c in cur.description or []]
    return dict(zip(names, row, strict=True))


def plans_for_field(conn: psycopg.Connection, org_id: UUID, field_id: UUID) -> list[PlanSummary]:
    with conn.cursor(row_factory=class_row(PlanSummary)) as cur:
        return cur.execute(
            _SUMMARY + " where p.organisation_id = %s and p.field_id = %s"
            " order by p.created_at desc",
            (org_id, field_id),
        ).fetchall()


def last_plan_per_field(conn: psycopg.Connection, org_id: UUID) -> dict[UUID, PlanSummary]:
    with conn.cursor() as cur:
        rows = cur.execute(
            "select distinct on (p.field_id) p.field_id, p.id from crop_plan p"
            " where p.organisation_id = %s order by p.field_id, p.created_at desc",
            (org_id,),
        ).fetchall()
    ids = {plan_id: field_id for field_id, plan_id in rows}
    if not ids:
        return {}
    with conn.cursor(row_factory=class_row(PlanSummary)) as cur:
        summaries = cur.execute(
            _SUMMARY + " where p.organisation_id = %s and p.id = any(%s)",
            (org_id, list(ids)),
        ).fetchall()
    return {ids[s.id]: s for s in summaries}


# Status of a plan = review state of its latest version (the one without a child).
# Only agronomist_approved approve/reject are final; an `ai_reviewed` review (D4, rule 11)
# leaves the plan in review.
_SUMMARY = (
    "select p.id, s.label as season_label, p.crop, p.plan_date,"
    " (select count(*) from recommendation r where r.organisation_id = p.organisation_id"
    "   and r.crop_plan_id = p.id)::int as versions,"
    " l.confidence::text as confidence,"
    " case when l.id is null then 'draft'"
    "   when exists (select 1 from review v where v.recommendation_id = l.id"
    "     and v.review_kind = 'agronomist_approved' and v.decision = 'approve') then 'approved'"
    "   when exists (select 1 from review v where v.recommendation_id = l.id"
    "     and v.review_kind = 'agronomist_approved' and v.decision = 'reject') then 'rejected'"
    "   else 'in_review' end as status,"
    " coalesce(greatest(l.created_at, (select max(v.created_at) from review v"
    "   where v.recommendation_id = l.id)), p.created_at) as updated_at"
    " from crop_plan p"
    " join season s on s.organisation_id = p.organisation_id and s.id = p.season_id"
    " left join lateral (select r.id, r.confidence, r.created_at from recommendation r"
    "   where r.organisation_id = p.organisation_id and r.crop_plan_id = p.id"
    "   and not exists (select 1 from recommendation c where c.parent_id = r.id)"
    "   order by r.created_at desc limit 1) l on true"
)
