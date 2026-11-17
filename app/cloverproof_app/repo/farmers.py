"""Farmers of one organisation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class FarmerRow:
    id: UUID
    display_name: str
    farm_count: int
    created_at: datetime


def list_farmers(conn: psycopg.Connection, org_id: UUID) -> list[FarmerRow]:
    with conn.cursor(row_factory=class_row(FarmerRow)) as cur:
        return cur.execute(
            "select f.id, f.display_name, f.created_at,"
            " (select count(*) from farm where farm.organisation_id = f.organisation_id"
            "  and farm.farmer_id = f.id)::int as farm_count"
            " from farmer f where f.organisation_id = %s"
            " order by lower(f.display_name), f.id",
            (org_id,),
        ).fetchall()
