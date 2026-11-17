"""Proof PDF data and wording rules. Proof PDF v0: one approved recommendation version -> HTML (Jinja2) -> PDF (WeasyPrint).

Pure rendering: no database, no storage, no clock. Identical `ProofInput` gives identical
bytes (no creation date in the PDF), so the SHA-256 is reproducible for the same document.

Wording rules (docs/design/webapp-ui.md §5, backend plan §2.10, reconciliation D4):
- no claim that any third party accepts, approves or certifies the document;
- "Approved by <name> (agronomist)" only when the approving review was made by a human;
  an AI review is never shown as an agronomist approval and the document stays DRAFT;
- a placeholder pack puts PLACEHOLDER_PACK_BANNER on every page.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

TEMPLATE_VERSION = "proof-v0"
PLACEHOLDER_PACK_BANNER = "Placeholder pack — not agronomic advice — test document"
NOT_YET_VALIDATED = "PLACEHOLDER — not yet validated"
HASH_STATEMENT = "SHA-256 of this file is recorded in CloverProof"

# Who made the approving review. Today every review is by a human app user (the review
# gate requires an `agronomist` membership). HOOK: when `review.actor_kind` exists
# (reconciliation D4, `ai_reviewed`), pass the column through; anything other than
# HUMAN_ACTOR is never rendered as an agronomist approval.
HUMAN_ACTOR = "human"
AI_ACTOR = "ai"

# Lowercase phrases that must never appear in a proof (checked by the tests on the
# rendered text). Our own reviewer line "Approved by <name> (agronomist)" is checked
# separately.
FORBIDDEN_PHRASES = (
    "accepted",
    "accepts",
    "certified",
    "certifies",
    "certificate",
    "compliant",
    "verified",
    "endorsed",
    "endorses",
    "guaranteed",
    "reviewed by an agronomist",
    "agronomist-approved",
)


@dataclass(frozen=True)
class Approval:
    reviewer_name: str
    approved_at: datetime
    actor_kind: str = HUMAN_ACTOR

    @property
    def by_human(self) -> bool:
        return self.actor_kind == HUMAN_ACTOR


@dataclass(frozen=True)
class ProofInput:
    document_id: UUID
    recommendation_id: UUID
    version_number: int
    farmer_name: str
    farm_name: str
    field_name: str
    previous_crop_label: str
    # The recommendation document as stored in `recommendation.result`.
    doc: dict[str, Any]
    # The approving review of this version; None renders a DRAFT.
    approval: Approval | None

    @property
    def is_final(self) -> bool:
        """A final proof needs an approval by a human agronomist (hard rule 8, D4)."""
        return self.approval is not None and self.approval.by_human

    @property
    def placeholder_pack(self) -> bool:
        return self.doc.get("pack_status") != "validated"


def approval_line(approval: Approval) -> str:
    when = approval.approved_at.strftime("%Y-%m-%d")
    if approval.by_human:
        return f"Approved by {approval.reviewer_name} (agronomist) on {when}"
    return (
        f"Reviewed by {approval.reviewer_name} (automated assistant, not a person) on {when}."
        " No human agronomist has approved this plan"
    )

