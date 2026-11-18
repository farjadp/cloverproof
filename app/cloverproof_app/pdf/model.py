"""Proof PDF data and wording rules. Proof PDF v0: one approved recommendation version ->
HTML (Jinja2) -> PDF (WeasyPrint).

Pure rendering: no database, no storage, no clock. Identical `ProofInput` gives identical
bytes (no creation date in the PDF), so the SHA-256 is reproducible for the same document.

Wording rules (CLAUDE.md rules 8 and 11, docs/design/webapp-ui.md):
- no claim that any third party (government, lender, buyer, certifier) accepts, approves
  or certifies the document;
- "Reviewed and approved by agronomist <name>" only for an `agronomist_approved` review;
  a `superadmin_approved` review says "platform administrator; not an agronomist review";
  an `ai_reviewed` review is never an approval and never makes an `Approval`;
- without an approval the document is a DRAFT (watermark on every page). The service
  never stores a draft: only approved versions get a `proof_document`;
- PLACEHOLDER values put PLACEHOLDER_BANNER on every page and "not yet validated" next to
  every number that depends on them.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

TEMPLATE_VERSION = "proof-v0"
PLACEHOLDER_BANNER = "PLACEHOLDER values — not for field use"
NOT_YET_VALIDATED = "PLACEHOLDER — not yet validated"
HASH_STATEMENT = "SHA-256 of this file is recorded in CloverProof"
NO_SOIL_TEST = "No soil test: N only; P/K soil test recommended"

# review.review_kind (migration 0012). Only the first two are human approvals.
AGRONOMIST_APPROVED = "agronomist_approved"
SUPERADMIN_APPROVED = "superadmin_approved"
AI_REVIEWED = "ai_reviewed"
APPROVAL_KINDS = frozenset({AGRONOMIST_APPROVED, SUPERADMIN_APPROVED})
APPROVAL_KIND_LABELS = {
    AGRONOMIST_APPROVED: "agronomist_approved (human agronomist of the organisation)",
    SUPERADMIN_APPROVED: "superadmin_approved (human platform administrator)",
}

# Lowercase phrases that must never appear in a proof (checked by the tests on the
# rendered text). Our own approval lines are checked separately.
FORBIDDEN_PHRASES = (
    "accepted",
    "accepts",
    "approved for",
    "certified",
    "certifies",
    "certificate",
    "compliant",
    "verified",
    "endorsed",
    "endorses",
    "guaranteed",
    "agronomist-approved",
)


class NotAnApproval(ValueError):
    """The review is not a human approval (e.g. `ai_reviewed`); no final proof."""


@dataclass(frozen=True)
class Approval:
    """The human approve review of the version the proof shows."""

    reviewer_name: str
    approved_at: datetime
    review_kind: str

    def __post_init__(self) -> None:
        if self.review_kind not in APPROVAL_KINDS:
            raise NotAnApproval(f"{self.review_kind!r} is not a human approval")

    @property
    def kind_label(self) -> str:
        return APPROVAL_KIND_LABELS[self.review_kind]

    @property
    def approved_at_utc(self) -> str:
        return self.approved_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


@dataclass(frozen=True)
class Version:
    """One version in the recommendation's lineage (v1 = engine)."""

    number: int
    recommendation_id: UUID
    kind: str  # engine | agronomist
    created_by_name: str
    created_at: datetime
    reason: str | None = None


@dataclass(frozen=True)
class Comparison:
    """Engine vs final for one number the reviewer changed (explained numbers)."""

    item: str
    engine: dict[str, Any]
    final: dict[str, Any]


@dataclass(frozen=True)
class ProofInput:
    document_id: UUID
    recommendation_id: UUID
    version_number: int
    farmer_name: str
    farm_name: str
    field_name: str
    season_label: str
    previous_crop_label: str
    # The recommendation document as stored in `recommendation.result`.
    doc: dict[str, Any]
    # The approving human review of this version; None renders a DRAFT.
    approval: Approval | None
    lineage: tuple[Version, ...] = ()
    comparison: tuple[Comparison, ...] = ()

    @property
    def is_final(self) -> bool:
        return self.approval is not None

    @property
    def uses_placeholder(self) -> bool:
        """Any PLACEHOLDER input: an unvalidated pack, a constant or a flagged number."""
        if self.doc.get("pack_status") != "validated":
            return True
        nitrogen = self.doc["nitrogen"]
        if any(c.get("status") == "PLACEHOLDER" for c in nitrogen.get("constants_used", [])):
            return True
        windows = [s.get("timing_window") or {} for s in nitrogen.get("splits", [])]
        if any(w.get("status") == "PLACEHOLDER" for w in windows):
            return True  # a timing window has no validated status yet (engine rule C6)
        return any(n.get("uses_placeholder") for n in explained_numbers(self.doc))

    @property
    def input_snapshot_sha256(self) -> str:
        return snapshot_sha256(self.doc["input_snapshot"])


def snapshot_sha256(snapshot: Any) -> str:
    """SHA-256 of the input snapshot as canonical JSON (sorted keys, no spaces, UTF-8)."""
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def explained_numbers(doc: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Every number in the document that carries its own explanation."""
    n = doc["nitrogen"]
    yield n["rate"]
    yield n["total"]
    yield from n["components"]
    for split in n["splits"]:
        yield split["fraction"]
        yield split["rate"]
        yield split["total"]


def approval_line(approval: Approval) -> str:
    """The reviewer line. Exact wording per review kind (CLAUDE.md rules 8 and 11)."""
    if approval.review_kind == AGRONOMIST_APPROVED:
        return f"Reviewed and approved by agronomist {approval.reviewer_name}"
    if approval.review_kind == SUPERADMIN_APPROVED:
        return (
            f"Approved by {approval.reviewer_name}"
            " (platform administrator; not an agronomist review)"
        )
    raise NotAnApproval(approval.review_kind)  # unreachable: __post_init__ refuses it
