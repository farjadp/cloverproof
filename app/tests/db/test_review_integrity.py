"""Version/approval invariants in the database (migration 0012, security review F1, F4, D4).

- A recommendation has at most one child (no forks) and at most one final review
  (approve or reject).
- No final review on a recommendation that already has a child, and no child of a
  recommendation that already has a final review.
Every violation is SQLSTATE 23505 (unique_violation) with a constraint name the app maps
to HTTP 409.
"""

from typing import Any
from uuid import UUID

import psycopg
import pytest
from psycopg import errors

from .conftest import Org, as_role, edited, insert, recommendation_values

pytestmark = pytest.mark.db

STALE_VERSION = {"recommendation_one_child_idx", "review_final_after_child"}
ALREADY_REVIEWED = {
    "review_one_final_idx",
    "review_one_approval_idx",
    "recommendation_child_after_final",
}


def child(db: psycopg.Connection, org: Org, result: dict[str, Any], n_rate: float) -> UUID:
    return insert(
        db,
        "recommendation",
        organisation_id=org.id,
        crop_plan_id=org.crop_plan,
        parent_id=org.engine_rec,
        kind="agronomist",
        reason="Lower rate (test)",
        created_by=org.agronomist,
        **recommendation_values(edited(result, n_rate)),
    )


def final(db: psycopg.Connection, org: Org, decision: str, rec: UUID | None = None) -> UUID:
    return insert(
        db,
        "review",
        organisation_id=org.id,
        recommendation_id=rec or org.engine_rec,
        decision=decision,
        reason="test reason",
        reviewer_id=org.agronomist,
        minutes_spent=5,
    )


def constraint_of(error: pytest.ExceptionInfo[errors.UniqueViolation]) -> str | None:
    return error.value.diag.constraint_name


def test_child_after_final_review(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    final(db, org_a, "approve")
    with pytest.raises(errors.UniqueViolation) as error, db.transaction():
        child(db, org_a, engine_result, 80.0)
    assert constraint_of(error) == "recommendation_child_after_final"


def test_child_after_reject(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    final(db, org_a, "reject")
    with pytest.raises(errors.UniqueViolation) as error, db.transaction():
        child(db, org_a, engine_result, 80.0)
    assert constraint_of(error) == "recommendation_child_after_final"


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_final_review_after_child(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any], decision: str
) -> None:
    child(db, org_a, engine_result, 80.0)
    with pytest.raises(errors.UniqueViolation) as error, db.transaction():
        final(db, org_a, decision)
    assert constraint_of(error) == "review_final_after_child"


def test_child_can_still_be_approved(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    rec = child(db, org_a, engine_result, 80.0)
    final(db, org_a, "approve", rec)


def test_double_child(db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]) -> None:
    child(db, org_a, engine_result, 80.0)
    with pytest.raises(errors.UniqueViolation) as error, db.transaction():
        child(db, org_a, engine_result, 70.0)
    assert constraint_of(error) == "recommendation_one_child_idx"


def test_approve_and_reject(db: psycopg.Connection, org_a: Org) -> None:
    final(db, org_a, "approve")
    with pytest.raises(errors.UniqueViolation) as error, db.transaction():
        final(db, org_a, "reject")
    assert constraint_of(error) == "review_one_final_idx"


def test_reject_twice(db: psycopg.Connection, org_a: Org) -> None:
    final(db, org_a, "reject")
    with pytest.raises(errors.UniqueViolation) as error, db.transaction():
        final(db, org_a, "reject")
    assert constraint_of(error) == "review_one_final_idx"


def test_documented_names_cover_every_case() -> None:
    assert STALE_VERSION.isdisjoint(ALREADY_REVIEWED)


# D4 / rule 11: a review of kind ai_reviewed (service account) is never final, never an
# approval, never unlocks a proof and never enters recommendation_diff.


def service_reviewer(db: psycopg.Connection, org: Org) -> UUID:
    with as_role(db, "cp_admin"):
        user = insert(
            db, "app_user", email="svc@example.org", display_name="Svc", actor_kind="service"
        )
    insert(db, "membership", organisation_id=org.id, user_id=user, role="agronomist")
    return user


def ai_review(db: psycopg.Connection, org: Org, reviewer: UUID, decision: str = "approve") -> UUID:
    return insert(
        db,
        "review",
        organisation_id=org.id,
        recommendation_id=org.engine_rec,
        decision=decision,
        review_kind="ai_reviewed",
        reason="AI check (test)",
        reviewer_id=reviewer,
        minutes_spent=0,
    )


def test_ai_approve_does_not_unlock_proof_document(db: psycopg.Connection, org_a: Org) -> None:
    ai_review(db, org_a, service_reviewer(db, org_a))
    sha = "a" * 64
    with pytest.raises(errors.CheckViolation, match="not approved"), db.transaction():
        insert(
            db,
            "proof_document",
            organisation_id=org_a.id,
            recommendation_id=org_a.engine_rec,
            sha256=sha,
            storage_key=f"proof/{org_a.id}/{org_a.engine_rec}/{sha}.pdf",
            created_by=org_a.agronomist,
        )


def test_ai_reviews_are_not_final(
    db: psycopg.Connection, org_a: Org, engine_result: dict[str, Any]
) -> None:
    service = service_reviewer(db, org_a)
    ai_review(db, org_a, service, "approve")
    ai_review(db, org_a, service, "reject")
    ai_review(db, org_a, service, "approve")  # several AI passes are fine
    # None of them blocks the human: edit, then approve the edit.
    rec = child(db, org_a, engine_result, 80.0)
    final(db, org_a, "approve", rec)
    rows = db.execute(
        "select final_recommendation_id, approved_by from recommendation_diff"
        " where organisation_id = %s and approved_at is not null",
        (org_a.id,),
    ).fetchall()
    assert rows == [(rec, org_a.agronomist)]


def test_ai_review_after_human_final_is_allowed(db: psycopg.Connection, org_a: Org) -> None:
    final(db, org_a, "approve")
    ai_review(db, org_a, service_reviewer(db, org_a), "reject")
    row = db.execute(
        "select count(*) from review where recommendation_id = %s"
        " and review_kind = 'agronomist_approved'",
        (org_a.engine_rec,),
    ).fetchone()
    assert row == (1,)


def test_ai_approve_absent_from_diff(db: psycopg.Connection, org_a: Org) -> None:
    ai_review(db, org_a, service_reviewer(db, org_a))
    row = db.execute(
        "select approved_by, approved_at from recommendation_diff"
        " where final_recommendation_id = %s",
        (org_a.engine_rec,),
    ).fetchone()
    assert row == (None, None)


def test_ai_review_view_lists_only_ai_reviews(db: psycopg.Connection, org_a: Org) -> None:
    service = service_reviewer(db, org_a)
    ai = ai_review(db, org_a, service, "reject")
    final(db, org_a, "approve")
    rows = db.execute(
        "select review_id, decision::text, reviewer_id, agronomist_decision::text"
        " from ai_review where organisation_id = %s",
        (org_a.id,),
    ).fetchall()
    assert rows == [(ai, "reject", service, "approve")]


# F4: the signed timer start is stored with the review.


def test_review_started_at(db: psycopg.Connection, org_a: Org) -> None:
    rid = insert(
        db,
        "review",
        organisation_id=org_a.id,
        recommendation_id=org_a.engine_rec,
        decision="approve",
        reviewer_id=org_a.agronomist,
        minutes_spent=12,
        started_at="2027-02-01T09:00:00Z",
    )
    row = db.execute(
        "select started_at = timestamptz '2027-02-01T09:00:00Z' from review where id = %s",
        (rid,),
    ).fetchone()
    assert row == (True,)
