"""Cached SoilGrids estimates of one field and season (migrations 0031, 0033).

Current rule: a row is current when its `field_location_revision` equals the field's revision
and it is the latest retrieval among that revision's rows for its property and depth. Older
rows stay stored (the table is immutable) and are superseded. Rows are never P or K (rule 3).

Coordinates are read only by `lock_field_point`, for the operator's load step; they are not on
any other type here and are never stored with an estimate (rule 12).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class CurrentEstimate:
    property: str
    depth_top_cm: int
    depth_bottom_cm: int
    statistic: str
    value: Decimal
    unit: str
    value_q05: Decimal | None
    value_q95: Decimal | None
    uncertainty_ratio: Decimal | None
    source: str
    source_version: str
    resolution_m: Decimal
    retrieved_at: datetime
    licence: str
    attribution: str
    citation: str
    layer_url: str
    field_location_revision: int

    @property
    def depth(self) -> str:
        """SoilGrids depth label, e.g. `0-5cm`."""
        return f"{self.depth_top_cm}-{self.depth_bottom_cm}cm"

    @property
    def retrieved_on(self) -> date:
        return self.retrieved_at.astimezone(UTC).date()


@dataclass(frozen=True)
class FieldPoint:
    # repr=False: a stray log line or traceback must not print the point.
    lat: Decimal = field(repr=False)
    lon: Decimal = field(repr=False)
    revision: int


@dataclass(frozen=True)
class NewEstimate:
    property: str
    depth_top_cm: int
    depth_bottom_cm: int
    statistic: str
    value: float
    unit: str
    value_q05: float | None
    value_q95: float | None
    uncertainty_ratio: float | None
    source: str
    source_version: str
    resolution_m: float
    retrieved_at: datetime
    licence: str
    attribution: str
    citation: str
    layer_url: str


@dataclass(frozen=True)
class EstimateSeason:
    id: UUID
    label: str
    has_current: bool  # holds a value for the field's present location
    has_estimates: bool  # holds any row for this field, of any location


def seasons_for_field(
    conn: psycopg.Connection, org_id: UUID, field_id: UUID
) -> list[EstimateSeason]:
    """Seasons used on the field's farm (plan, area or estimate), newest label first."""
    with conn.cursor(row_factory=class_row(EstimateSeason)) as cur:
        return cur.execute(
            "select s.id, s.label,"
            " exists (select 1 from soil_estimate se"
            "   where se.organisation_id = s.organisation_id and se.field_id = f.id"
            "     and se.season_id = s.id"
            "     and se.field_location_revision = f.location_revision) as has_current,"
            " exists (select 1 from soil_estimate se"
            "   where se.organisation_id = s.organisation_id and se.field_id = f.id"
            "     and se.season_id = s.id) as has_estimates"
            " from field f join season s on s.organisation_id = f.organisation_id"
            " where f.organisation_id = %(org)s and f.id = %(field)s and s.id in ("
            "   select used.season_id from field sibling"
            "   join lateral ("
            "     select p.season_id from crop_plan p"
            "       where p.organisation_id = sibling.organisation_id"
            "         and p.field_id = sibling.id"
            "     union select g.season_id from field_geometry_version g"
            "       where g.organisation_id = sibling.organisation_id"
            "         and g.field_id = sibling.id"
            "     union select e.season_id from soil_estimate e"
            "       where e.organisation_id = sibling.organisation_id"
            "         and e.field_id = sibling.id"
            "   ) used on true"
            "   where sibling.organisation_id = f.organisation_id"
            "     and sibling.farm_id = f.farm_id)"
            " order by s.label desc, s.created_at desc, s.id",
            {"org": org_id, "field": field_id},
        ).fetchall()


def current_estimates(
    conn: psycopg.Connection, org_id: UUID, field_id: UUID, season_id: UUID
) -> list[CurrentEstimate]:
    """The current value per property and depth; empty if none, or the field is not visible."""
    with conn.cursor(row_factory=class_row(CurrentEstimate)) as cur:
        return cur.execute(
            "select distinct on (se.property, se.depth_top_cm, se.depth_bottom_cm)"
            " se.property, se.depth_top_cm, se.depth_bottom_cm, se.statistic, se.value, se.unit,"
            " se.value_q05, se.value_q95, se.uncertainty_ratio, se.source, se.source_version,"
            " se.resolution_m, se.retrieved_at, se.licence, se.attribution, se.citation,"
            " se.layer_url, se.field_location_revision"
            " from soil_estimate se"
            " join field f on f.organisation_id = se.organisation_id and f.id = se.field_id"
            " where se.organisation_id = %s and se.field_id = %s and se.season_id = %s"
            "   and se.field_location_revision = f.location_revision"
            " order by se.property, se.depth_top_cm, se.depth_bottom_cm,"
            "   se.retrieved_at desc, se.created_at desc, se.id desc",
            (org_id, field_id, season_id),
        ).fetchall()


def has_stale_estimates(
    conn: psycopg.Connection, org_id: UUID, field_id: UUID, season_id: UUID
) -> bool:
    """True if a stored property and depth has only rows of an earlier location.

    Rows from before migration 0033 (NULL revision) count as earlier. Once a load has replaced
    a property and depth, its old rows stay stored but no longer make this True.
    """
    row = conn.execute(
        "select exists (select 1 from soil_estimate se"
        " join field f on f.organisation_id = se.organisation_id and f.id = se.field_id"
        " where se.organisation_id = %(org)s and se.field_id = %(field)s"
        "   and se.season_id = %(season)s"
        "   and se.field_location_revision is distinct from f.location_revision"
        "   and not exists (select 1 from soil_estimate c"
        "     where c.organisation_id = se.organisation_id and c.field_id = se.field_id"
        "       and c.season_id = se.season_id and c.property = se.property"
        "       and c.depth_top_cm = se.depth_top_cm"
        "       and c.depth_bottom_cm = se.depth_bottom_cm"
        "       and c.field_location_revision = f.location_revision))",
        {"org": org_id, "field": field_id, "season": season_id},
    ).fetchone()
    assert row is not None
    return bool(row[0])


def field_record_kind(conn: psycopg.Connection, org_id: UUID, field_id: UUID) -> str | None:
    """`farmer.record_kind` behind the field; None if the field is not in this organisation."""
    row = conn.execute(
        "select fr.record_kind from field fi"
        " join farm fa on fa.organisation_id = fi.organisation_id and fa.id = fi.farm_id"
        " join farmer fr on fr.organisation_id = fa.organisation_id and fr.id = fa.farmer_id"
        " where fi.organisation_id = %s and fi.id = %s",
        (org_id, field_id),
    ).fetchone()
    return row[0] if row else None


def season_exists(conn: psycopg.Connection, org_id: UUID, season_id: UUID) -> bool:
    row = conn.execute(
        "select 1 from season where organisation_id = %s and id = %s", (org_id, season_id)
    ).fetchone()
    return row is not None


def lock_field_point(conn: psycopg.Connection, org_id: UUID, field_id: UUID) -> FieldPoint | None:
    """The field's point, held against a move until commit; None if it has no location."""
    row = conn.execute(
        "select location_lat, location_lon, location_revision from field"
        " where organisation_id = %s and id = %s for share",
        (org_id, field_id),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return FieldPoint(lat=row[0], lon=row[1], revision=row[2])


def insert_estimate(
    conn: psycopg.Connection,
    org_id: UUID,
    *,
    field_id: UUID,
    season_id: UUID,
    revision: int,
    created_by: UUID,
    estimate: NewEstimate,
) -> None:
    conn.execute(
        "insert into soil_estimate (organisation_id, field_id, season_id,"
        " field_location_revision, created_by, property, depth_top_cm, depth_bottom_cm,"
        " statistic, value, unit, value_q05, value_q95, uncertainty_ratio, source,"
        " source_version, resolution_m, retrieved_at, licence, attribution, citation, layer_url)"
        " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
        " %s, %s, %s)",
        (
            org_id,
            field_id,
            season_id,
            revision,
            created_by,
            estimate.property,
            estimate.depth_top_cm,
            estimate.depth_bottom_cm,
            estimate.statistic,
            estimate.value,
            estimate.unit,
            estimate.value_q05,
            estimate.value_q95,
            estimate.uncertainty_ratio,
            estimate.source,
            estimate.source_version,
            estimate.resolution_m,
            estimate.retrieved_at,
            estimate.licence,
            estimate.attribution,
            estimate.citation,
            estimate.layer_url,
        ),
    )
