"""Farmers, farms, fields, seasons and manual field areas of one organisation.

Every function takes `org_id` and filters by it; a row of another organisation is
"not found" (None), never an error that reveals it exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class Farmer:
    id: UUID
    display_name: str
    notes: str | None


@dataclass(frozen=True)
class FieldRow:
    id: UUID
    name: str
    farm_id: UUID
    farm_name: str
    farmer_id: UUID
    farmer_name: str
    area_ha: Decimal | None
    area_season: str | None


@dataclass(frozen=True)
class FarmRow:
    id: UUID
    name: str


@dataclass(frozen=True)
class OverviewRow:
    """One line of the Farmers table: a farmer and one of their farms (or none)."""

    farmer_id: UUID
    farmer_name: str
    farm_id: UUID | None
    farm_name: str | None


def create_farmer(conn: psycopg.Connection, org_id: UUID, *, display_name: str,
                  notes: str | None) -> UUID:  # fmt: skip
    row = conn.execute(
        "insert into farmer (organisation_id, display_name, notes) values (%s, %s, %s)"
        " returning id",
        (org_id, display_name.strip(), notes),
    ).fetchone()
    assert row is not None
    return row[0]


def get_farmer(conn: psycopg.Connection, org_id: UUID, farmer_id: UUID) -> Farmer | None:
    with conn.cursor(row_factory=class_row(Farmer)) as cur:
        return cur.execute(
            "select id, display_name, notes from farmer where organisation_id = %s and id = %s",
            (org_id, farmer_id),
        ).fetchone()


def like_pattern(q: str) -> str:
    """`%q%` for LIKE, with the user's `\\`, `%` and `_` matched literally (N15)."""
    escaped = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def overview(conn: psycopg.Connection, org_id: UUID, q: str = "") -> list[OverviewRow]:
    """Farmers with their farms; `q` filters by farmer, farm or field name."""
    pattern = like_pattern(q)
    with conn.cursor(row_factory=class_row(OverviewRow)) as cur:
        return cur.execute(
            "select f.id as farmer_id, f.display_name as farmer_name,"
            " fa.id as farm_id, fa.name as farm_name"
            " from farmer f left join farm fa"
            "   on fa.organisation_id = f.organisation_id and fa.farmer_id = f.id"
            " where f.organisation_id = %(org)s and (%(all)s"
            "   or lower(f.display_name) like %(q)s escape '\\'"
            "   or lower(coalesce(fa.name, '')) like %(q)s escape '\\'"
            "   or exists (select 1 from field fi where fi.organisation_id = f.organisation_id"
            "     and fi.farm_id = fa.id and lower(fi.name) like %(q)s escape '\\'))"
            " order by lower(f.display_name), f.id, lower(fa.name), fa.id",
            {"org": org_id, "q": pattern, "all": not q.strip()},
        ).fetchall()


def list_farms(conn: psycopg.Connection, org_id: UUID, farmer_id: UUID) -> list[FarmRow]:
    with conn.cursor(row_factory=class_row(FarmRow)) as cur:
        return cur.execute(
            "select id, name from farm where organisation_id = %s and farmer_id = %s"
            " order by lower(name), id",
            (org_id, farmer_id),
        ).fetchall()


def create_farm(conn: psycopg.Connection, org_id: UUID, *, farmer_id: UUID, name: str) -> UUID:
    row = conn.execute(
        "insert into farm (organisation_id, farmer_id, name) values (%s, %s, %s) returning id",
        (org_id, farmer_id, name.strip()),
    ).fetchone()
    assert row is not None
    return row[0]


_FIELD_SELECT = (
    "select fi.id, fi.name, fa.id as farm_id, fa.name as farm_name,"
    " fr.id as farmer_id, fr.display_name as farmer_name,"
    " g.area_ha, g.label as area_season"
    " from field fi"
    " join farm fa on fa.organisation_id = fi.organisation_id and fa.id = fi.farm_id"
    " join farmer fr on fr.organisation_id = fa.organisation_id and fr.id = fa.farmer_id"
    " left join lateral (select gv.area_ha, s.label from field_geometry_version gv"
    "   join season s on s.organisation_id = gv.organisation_id and s.id = gv.season_id"
    "   where gv.organisation_id = fi.organisation_id and gv.field_id = fi.id"
    "   order by s.label desc limit 1) g on true"
)


def get_field(conn: psycopg.Connection, org_id: UUID, field_id: UUID) -> FieldRow | None:
    with conn.cursor(row_factory=class_row(FieldRow)) as cur:
        return cur.execute(
            _FIELD_SELECT + " where fi.organisation_id = %s and fi.id = %s", (org_id, field_id)
        ).fetchone()


def fields_of_farmer(conn: psycopg.Connection, org_id: UUID, farmer_id: UUID) -> list[FieldRow]:
    with conn.cursor(row_factory=class_row(FieldRow)) as cur:
        return cur.execute(
            _FIELD_SELECT + " where fi.organisation_id = %s and fr.id = %s"
            " order by lower(fa.name), lower(fi.name), fi.id",
            (org_id, farmer_id),
        ).fetchall()


def fields_of_org(conn: psycopg.Connection, org_id: UUID) -> list[FieldRow]:
    with conn.cursor(row_factory=class_row(FieldRow)) as cur:
        return cur.execute(
            _FIELD_SELECT + " where fi.organisation_id = %s order by lower(fi.name), fi.id",
            (org_id,),
        ).fetchall()


def create_field(conn: psycopg.Connection, org_id: UUID, *, farm_id: UUID, name: str) -> UUID:
    row = conn.execute(
        "insert into field (organisation_id, farm_id, name) values (%s, %s, %s) returning id",
        (org_id, farm_id, name.strip()),
    ).fetchone()
    assert row is not None
    return row[0]


def season_for(conn: psycopg.Connection, org_id: UUID, day: date) -> UUID:
    """The organisation's season for a date: label = calendar year (created if missing)."""
    label = str(day.year)
    conn.execute(
        "insert into season (organisation_id, label) values (%s, %s)"
        " on conflict (organisation_id, label) do nothing",
        (org_id, label),
    )
    row = conn.execute(
        "select id from season where organisation_id = %s and label = %s", (org_id, label)
    ).fetchone()
    assert row is not None
    return row[0]


def set_manual_area(conn: psycopg.Connection, org_id: UUID, *, field_id: UUID, season_id: UUID,
                    area_ha: float, user_id: UUID) -> None:  # fmt: skip
    """Hand-entered area for the field in this season (geometry stays NULL until Phase 4)."""
    conn.execute(
        "insert into field_geometry_version"
        " (organisation_id, field_id, season_id, area_ha, area_source, created_by)"
        " values (%s, %s, %s, %s, 'manual', %s)"
        " on conflict (field_id, season_id) do update set area_ha = excluded.area_ha"
        " where field_geometry_version.organisation_id = excluded.organisation_id"
        " and field_geometry_version.area_source = 'manual'",
        (org_id, field_id, season_id, area_ha, user_id),
    )
