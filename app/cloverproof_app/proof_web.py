"""Proof PDF routes: generate (POST, CSRF) and download (GET), org-scoped.

Rules (CLAUDE.md rules 4, 5, 8, 11; ADR 0005 B1):
- only the latest version of a plan with a human approve review (`agronomist_approved`
  or `superadmin_approved`) gets a proof; `ai_reviewed` never does. The service refuses
  with 409, and the database trigger `proof_document_check_approved` refuses again;
- one proof per approved version: a second request returns the existing document, it
  never renders a replacement. A new version (edit) is a new recommendation, so a new
  document;
- the SHA-256 of the exact PDF bytes is stored in `proof_document` (insert-only) and the
  file in the ProofStore under `proof/{org_id}/{recommendation_id}/{sha256}.pdf`
  (write-once). Every download re-hashes the bytes and refuses a mismatch;
- signed-in human members of the organisation only; another organisation's ids are 404.
  Service accounts (the AI reviewer) never generate or download a proof: it carries
  farmer data (rule 12).
"""

from __future__ import annotations

import base64
import binascii
import logging
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse, Response

from cloverproof_app import plan_web, planning
from cloverproof_app.auth import Conn, OrgContext, SettingsDep
from cloverproof_app.pdf import (
    Approval,
    Comparison,
    PdfUnavailable,
    ProofInput,
    Version,
    render_pdf,
)
from cloverproof_app.plan_web import HUMAN_REVIEWS, InternalOrg, PlanView, not_found
from cloverproof_app.repo import proofs
from cloverproof_app.storage import (
    KeyExists,
    ProofNotFound,
    ProofStore,
    filesystem_store,
    proof_key,
    sha256_hex,
)
from cloverproof_app.web import render

router = APIRouter()
log = logging.getLogger(__name__)

NOT_APPROVED = (
    "Only a plan version approved by a human agronomist or superadmin gets a proof PDF."
    " Nothing was saved."
)
HUMANS_ONLY = "Proof documents are for signed-in people only."
PDF_UNAVAILABLE = (
    "PDF rendering is not available on this server (WeasyPrint system libraries are"
    " missing). Nothing was saved."
)
TAMPERED = (
    "The stored file does not match the SHA-256 recorded for this document, so it is not"
    " served. Report this document ID."
)
FILE_MISSING = "The file for this document is missing from storage. Report this document ID."


def proof_store(request: Request, settings: SettingsDep) -> ProofStore:
    """The app's ProofStore (tests set `app.state.proof_store`); filesystem by default."""
    store: ProofStore | None = getattr(request.app.state, "proof_store", None)
    if store is None:
        store = filesystem_store(settings.proof_store_dir)
        request.app.state.proof_store = store
    return store


def require_human(context: OrgContext) -> None:
    if not context.user.is_human:
        raise HTTPException(403, HUMANS_ONLY)


def approval_of(view: PlanView) -> Approval:
    """The human approval of the version on screen, or 409."""
    final = view.final_review
    if (
        view.status != "approved"
        or final is None
        or final.decision != "approve"
        or final.review_kind not in HUMAN_REVIEWS
        or final.recommendation_id != view.latest.id
    ):
        raise HTTPException(409, NOT_APPROVED)
    return Approval(final.reviewer_name, final.created_at, final.review_kind)


def proof_input(request: Request, view: PlanView, approval: Approval,
                document_id: UUID) -> ProofInput:  # fmt: skip
    pack = request.app.state.pack
    previous = dict(planning.previous_crop_choices(pack)).get(
        view.plan.previous_crop, view.plan.previous_crop
    )
    upto = view.versions[: view.versions.index(view.latest) + 1]
    lineage = tuple(
        Version(i + 1, v.id, v.kind, v.created_by_name, v.created_at, v.reason)
        for i, v in enumerate(upto)
    )
    rows = tuple(Comparison(r["item"], r["engine"], r["final"]) for r in plan_web.comparison(view))
    return ProofInput(
        document_id=document_id,
        recommendation_id=view.latest.id,
        version_number=view.number,
        farmer_name=view.field.farmer_name,
        farm_name=view.field.farm_name,
        field_name=view.field.name,
        season_label=view.plan.season_label,
        previous_crop_label=previous,
        doc=view.doc,
        approval=approval,
        lineage=lineage,
        comparison=rows,
    )


def store_once(store: ProofStore, key: str, data: bytes) -> None:
    """Write-once put. An existing key is accepted only if it holds exactly these bytes."""
    try:
        store.put(key, data)
    except KeyExists:
        if store.get(key) != data:
            raise


@router.post("/plans/{plan_id}/proof")
async def proof_generate(request: Request, conn: Conn, context: InternalOrg,
                         settings: SettingsDep, plan_id: UUID) -> Response:  # fmt: skip
    require_human(context)
    org = context.org.id
    view = plan_web.locked_plan(conn, context, plan_id)  # one generation per plan at a time
    approval = approval_of(view)
    existing = proofs.for_recommendation(conn, org, view.latest.id)
    if existing:  # never render over an existing document
        return RedirectResponse(f"/proofs/{existing[0].id}", status_code=303)

    document_id = uuid4()
    proof = proof_input(request, view, approval, document_id)
    try:
        data = await run_in_threadpool(render_pdf, proof)
    except PdfUnavailable as error:
        log.error("proof PDF unavailable: %s", error)
        raise HTTPException(503, PDF_UNAVAILABLE) from error
    sha256 = sha256_hex(data)
    key = proof_key(org, view.latest.id, sha256)
    try:
        with conn.transaction():  # the DB trigger checks the approval a second time
            proofs.insert(conn, org, document_id=document_id, recommendation_id=view.latest.id,
                          sha256=sha256, storage_key=key, user_id=context.user.id)  # fmt: skip
    except psycopg.errors.CheckViolation as error:
        raise HTTPException(409, NOT_APPROVED) from error
    # After the row: if the write fails, the request's transaction rolls the row back.
    store_once(proof_store(request, settings), key, data)
    log.info("proof %s stored for recommendation %s (%s)", document_id, view.latest.id, sha256)
    return RedirectResponse(f"/proofs/{document_id}", status_code=303)


def load_proof(conn: Conn, context: OrgContext, document_id: UUID) -> proofs.ProofRow:
    require_human(context)
    row = proofs.get(conn, context.org.id, document_id)
    if row is None:
        raise not_found("Proof document")
    return row


@router.get("/plans/{plan_id}/proof")
def proof_panel(request: Request, conn: Conn, context: InternalOrg, plan_id: UUID) -> Response:
    """Proof section of the plan page (loaded by htmx): the document, or the button."""
    require_human(context)
    view = plan_web.load_plan(conn, context, plan_id)
    docs = proofs.for_recommendation(conn, context.org.id, view.latest.id)
    approved = view.status == "approved"
    return render(request, "_proof_panel.html", {"v": view, "docs": docs, "approved": approved})


@router.get("/proofs/{document_id}")
def proof_detail(request: Request, conn: Conn, context: InternalOrg,
                 document_id: UUID) -> Response:  # fmt: skip
    row = load_proof(conn, context, document_id)
    plan = plan_web.load_plan(conn, context, row.crop_plan_id)
    return render(request, "proof_document.html", {"d": row, "v": plan})


@router.get("/proofs/{document_id}/download")
def proof_download(request: Request, conn: Conn, context: InternalOrg, settings: SettingsDep,
                   document_id: UUID) -> Response:  # fmt: skip
    row = load_proof(conn, context, document_id)
    try:
        data = proof_store(request, settings).get(row.storage_key)
    except ProofNotFound as error:
        log.error("proof %s: file missing at %s", row.id, row.storage_key)
        raise HTTPException(500, FILE_MISSING) from error
    if sha256_hex(data) != row.sha256:
        log.error("proof %s: stored bytes do not match the recorded SHA-256", row.id)
        raise HTTPException(500, TAMPERED)
    digest = base64.b64encode(binascii.unhexlify(row.sha256)).decode("ascii")
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="cloverproof-proof-{row.id}.pdf"',
            "Repr-Digest": f"sha-256=:{digest}:",  # RFC 9530
        },
    )
