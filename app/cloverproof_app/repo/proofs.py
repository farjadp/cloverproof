"""Proof documents (insert-only; migrations 0008, 0012).

Every function takes `org_id` and filters by it. `proof_document` rows are never updated
or deleted (database triggers); the database also refuses a row for a recommendation
without a human approve review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg
from psycopg.rows import class_row


@dataclass(frozen=True)
class ProofRow:
    id: UUID
    recommendation_id: UUID
    crop_plan_id: UUID
    sha256: str
    storage_key: str
    created_by_name: str
    created_at: datetime


_SELECT = (
    "select d.id, d.recommendation_id, r.crop_plan_id, d.sha256::text as sha256,"
    " d.storage_key, u.display_name as created_by_name, d.created_at"
    " from proof_document d"
    " join recommendation r on r.organisation_id = d.organisation_id"
    "   and r.id = d.recommendation_id"
    " join app_user u on u.id = d.created_by"
)


def get(conn: psycopg.Connection, org_id: UUID, document_id: UUID) -> ProofRow | None:
    with conn.cursor(row_factory=class_row(ProofRow)) as cur:
        return cur.execute(
            _SELECT + " where d.organisation_id = %s and d.id = %s", (org_id, document_id)
        ).fetchone()


def for_recommendation(conn: psycopg.Connection, org_id: UUID,
                       recommendation_id: UUID) -> list[ProofRow]:  # fmt: skip
    with conn.cursor(row_factory=class_row(ProofRow)) as cur:
        return cur.execute(
            _SELECT + " where d.organisation_id = %s and d.recommendation_id = %s"
            " order by d.created_at, d.id",
            (org_id, recommendation_id),
        ).fetchall()


def insert(conn: psycopg.Connection, org_id: UUID, *, document_id: UUID, recommendation_id: UUID,
           sha256: str, storage_key: str, user_id: UUID) -> None:  # fmt: skip
    """INSERT only. The id is chosen by the caller because it is printed in the PDF."""
    conn.execute(
        "insert into proof_document (id, organisation_id, recommendation_id, sha256,"
        " storage_key, created_by) values (%s, %s, %s, %s, %s, %s)",
        (document_id, org_id, recommendation_id, sha256, storage_key, user_id),
    )
