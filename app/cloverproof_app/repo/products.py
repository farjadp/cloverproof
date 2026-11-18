"""`fertilizer_product` catalog queries (migration 0027, ADR 0008 class `catalog`).

A global list of label facts: no organisation filter here. The database decides who sees
and writes what (RLS on app.user_id / app.platform_role). Writes run in a savepoint, so a
refusal leaves the request's transaction usable for rendering the error page.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class Product:
    id: UUID
    country_code: str
    name: str
    n: Decimal
    p2o5: Decimal
    k2o: Decimal
    s: Decimal
    form: str  # granular | liquid
    density_kg_per_l: Decimal | None
    status: str  # draft | active
    grade_source: str


@dataclass(frozen=True)
class NewProduct:
    country_code: str
    name: str
    n: Decimal
    p2o5: Decimal
    k2o: Decimal
    s: Decimal
    form: str
    density_kg_per_l: Decimal | None
    grade_source: str


class Activation(Enum):
    ACTIVATED = "activated"
    ALREADY_ACTIVE = "already_active"
    NOT_FOUND = "not_found"


def list_products(conn: psycopg.Connection, *, include_drafts: bool) -> list[Product]:
    """Active products, plus drafts (first) when asked. RLS still hides drafts from
    anyone who may not write them."""
    where = "" if include_drafts else "where status = 'active'"
    sql = (
        "select id, country_code, name, n, p2o5, k2o, s, form, density_kg_per_l, status,"
        f" grade_source from fertilizer_product {where}"
        " order by status = 'draft' desc, country_code, lower(name), id"
    )
    with conn.cursor(row_factory=class_row(Product)) as cur:
        return cur.execute(sql).fetchall()  # type: ignore[arg-type]


def active_name_exists(conn: psycopg.Connection, country_code: str, name: str) -> bool:
    """Same test as the unique index: per country, ignoring case."""
    row = conn.execute(
        "select 1 from fertilizer_product"
        " where status = 'active' and country_code = %s and lower(name) = lower(%s)",
        (country_code, name),
    ).fetchone()
    return row is not None


def add_draft(conn: psycopg.Connection, product: NewProduct, *, created_by: UUID) -> UUID:
    with conn.transaction():
        row = conn.execute(
            "insert into fertilizer_product (country_code, name, n, p2o5, k2o, s, form,"
            " density_kg_per_l, grade_source, created_by)"
            " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
            (
                product.country_code,
                product.name,
                product.n,
                product.p2o5,
                product.k2o,
                product.s,
                product.form,
                product.density_kg_per_l,
                product.grade_source,
                created_by,
            ),
        ).fetchone()
    assert row is not None
    return row[0]


def activate(conn: psycopg.Connection, product_id: UUID) -> Activation:
    with conn.transaction():
        updated = conn.execute(
            "update fertilizer_product set status = 'active'"
            " where id = %s and status = 'draft' returning id",
            (product_id,),
        ).fetchone()
    if updated is not None:
        return Activation.ACTIVATED
    row = conn.execute(
        "select 1 from fertilizer_product where id = %s and status = 'active'", (product_id,)
    ).fetchone()
    return Activation.ALREADY_ACTIVE if row is not None else Activation.NOT_FOUND
