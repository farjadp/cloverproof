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


class DraftChange(Enum):
    DONE = "done"
    NOT_A_DRAFT = "not_a_draft"
    NOT_FOUND = "not_found"
    REFUSED = "refused"  # still a visible draft, yet the statement touched nothing


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


def get_product(conn: psycopg.Connection, product_id: UUID) -> Product | None:
    """One product, if RLS lets this user see it (drafts: a superadmin only)."""
    with conn.cursor(row_factory=class_row(Product)) as cur:
        return cur.execute(
            "select id, country_code, name, n, p2o5, k2o, s, form, density_kg_per_l, status,"
            " grade_source from fertilizer_product where id = %s",
            (product_id,),
        ).fetchone()


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


def activate(
    conn: psycopg.Connection, product_id: UUID, *, grade_source: str | None = None
) -> Activation:
    """Draft -> active. A given grade_source replaces the source of the draft."""
    with conn.transaction():
        updated = conn.execute(
            "update fertilizer_product set status = 'active',"
            " grade_source = coalesce(%s, grade_source)"
            " where id = %s and status = 'draft' returning id",
            (grade_source, product_id),
        ).fetchone()
    if updated is not None:
        return Activation.ACTIVATED
    row = conn.execute(
        "select 1 from fertilizer_product where id = %s and status = 'active'", (product_id,)
    ).fetchone()
    return Activation.ALREADY_ACTIVE if row is not None else Activation.NOT_FOUND


def _why_unchanged(conn: psycopg.Connection, product_id: UUID) -> DraftChange:
    row = conn.execute(
        "select status from fertilizer_product where id = %s", (product_id,)
    ).fetchone()
    if row is None:
        return DraftChange.NOT_FOUND
    return DraftChange.REFUSED if row[0] == "draft" else DraftChange.NOT_A_DRAFT


def update_draft(conn: psycopg.Connection, product_id: UUID, product: NewProduct) -> DraftChange:
    """Replace a draft's label facts. Status and author are never touched here."""
    with conn.transaction():
        updated = conn.execute(
            "update fertilizer_product set country_code = %s, name = %s, n = %s, p2o5 = %s,"
            " k2o = %s, s = %s, form = %s, density_kg_per_l = %s, grade_source = %s"
            " where id = %s and status = 'draft' returning id",
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
                product_id,
            ),
        ).fetchone()
    return DraftChange.DONE if updated is not None else _why_unchanged(conn, product_id)


def delete_draft(conn: psycopg.Connection, product_id: UUID) -> DraftChange:
    with conn.transaction():
        deleted = conn.execute(
            "delete from fertilizer_product where id = %s and status = 'draft' returning id",
            (product_id,),
        ).fetchone()
    return DraftChange.DONE if deleted is not None else _why_unchanged(conn, product_id)
