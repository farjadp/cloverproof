"""Proof PDF routes end to end (TestClient + real database, filesystem ProofStore).

Most tests replace the WeasyPrint step with a recording fake (the HTML is what WeasyPrint
renders; `test_pdf_render.py` covers the real PDF). `test_real_pdf_*` renders with
WeasyPrint and skips when its system libraries are missing (fails under
CP_PDF_TESTS_REQUIRED=1, as in CI).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from fastapi.testclient import TestClient

from cloverproof_app import proof_web
from cloverproof_app.pdf import ProofInput, render_html
from cloverproof_app.storage import FilesystemProofStore, KeyExists, sha256_hex

from .conftest import Org, insert
from .test_actor_kind import make_service
from .test_plan_flow import signed_in
from .test_superadmin import make_user

pytestmark = pytest.mark.db


def review(db: psycopg.Connection, org: Org, reviewer: UUID, decision: str = "approve",
           reason: str | None = None) -> None:  # fmt: skip
    insert(db, "review", organisation_id=org.id, recommendation_id=org.engine_rec,
           decision=decision, reviewer_id=reviewer, minutes_spent=5,
           reason=reason or (None if decision == "approve" else "test reason"))  # fmt: skip


class FakeRender:
    """Records the ProofInput; returns deterministic bytes built from the real HTML."""

    def __init__(self) -> None:
        self.inputs: list[ProofInput] = []

    def __call__(self, proof: ProofInput) -> bytes:
        self.inputs.append(proof)
        return b"%PDF-fake\n" + render_html(proof).encode("utf-8")


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeRender:
    renderer = FakeRender()
    monkeypatch.setattr(proof_web, "render_pdf", renderer)
    return renderer


def client_for(db: psycopg.Connection, user: UUID, root: Path) -> tuple[TestClient, str]:
    client, csrf = signed_in(db, user)
    client.app.state.proof_store = FilesystemProofStore(root)  # type: ignore[attr-defined]
    return client, csrf


def generate(client: TestClient, csrf: str, org: Org) -> Any:
    return client.post(f"/plans/{org.crop_plan}/proof", data={"csrf_token": csrf})


def documents(db: psycopg.Connection, org: Org) -> list[tuple[Any, ...]]:
    return db.execute(
        "select id, sha256::text, storage_key from proof_document where organisation_id = %s",
        (org.id,),
    ).fetchall()


def test_unapproved_plan_is_refused(
    db: psycopg.Connection, org_a: Org, tmp_path: Path, fake: FakeRender
) -> None:
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    r = generate(client, csrf, org_a)
    assert r.status_code == 409 and "Nothing was saved" in r.text
    assert documents(db, org_a) == [] and fake.inputs == []
    assert "Generate proof PDF" not in client.get(f"/plans/{org_a.crop_plan}").text


def test_rejected_plan_is_refused(
    db: psycopg.Connection, org_a: Org, tmp_path: Path, fake: FakeRender
) -> None:
    review(db, org_a, org_a.agronomist, "reject")
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    assert generate(client, csrf, org_a).status_code == 409
    assert documents(db, org_a) == []


def test_ai_reviewed_plan_is_refused(
    db: psycopg.Connection, org_a: Org, tmp_path: Path, fake: FakeRender
) -> None:
    review(db, org_a, make_service(db, org_a), "approve", "AI opinion")  # ai_reviewed
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    assert generate(client, csrf, org_a).status_code == 409
    assert documents(db, org_a) == [] and fake.inputs == []


def test_csrf_required(
    db: psycopg.Connection, org_a: Org, tmp_path: Path, fake: FakeRender
) -> None:
    review(db, org_a, org_a.agronomist)
    client, _ = client_for(db, org_a.agronomist, tmp_path)
    r = client.post(f"/plans/{org_a.crop_plan}/proof", data={})
    assert r.status_code == 403
    assert documents(db, org_a) == []


def test_agronomist_approved_generates_stores_and_downloads(
    db: psycopg.Connection, org_a: Org, tmp_path: Path, fake: FakeRender
) -> None:
    review(db, org_a, org_a.agronomist)
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    assert "Generate proof PDF" in client.get(f"/plans/{org_a.crop_plan}").text
    r = generate(client, csrf, org_a)
    assert r.status_code == 303, r.text
    [(doc_id, sha, key)] = documents(db, org_a)
    assert r.headers["location"] == f"/proofs/{doc_id}"
    assert key == f"proof/{org_a.id}/{org_a.engine_rec}/{sha}.pdf"

    [proof] = fake.inputs
    assert proof.document_id == doc_id and proof.recommendation_id == org_a.engine_rec
    html = render_html(proof)
    assert "Reviewed and approved by agronomist Agro a" in html
    assert "platform administrator" not in html

    stored = (tmp_path / key).read_bytes()
    assert sha256_hex(stored) == sha  # stored hash = sha256(exact bytes)
    download = client.get(f"/proofs/{doc_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content == stored
    assert client.get(f"/proofs/{doc_id}").status_code == 200
    panel = client.get(f"/plans/{org_a.crop_plan}/proof").text
    assert str(doc_id) in panel and sha in panel and "Generate proof PDF" not in panel

    # A second request never renders over the existing document.
    again = generate(client, csrf, org_a)
    assert again.status_code == 303 and again.headers["location"] == f"/proofs/{doc_id}"
    assert len(documents(db, org_a)) == 1 and len(fake.inputs) == 1


def test_superadmin_approved_wording(
    db: psycopg.Connection, org_a: Org, tmp_path: Path, fake: FakeRender
) -> None:
    review(db, org_a, make_user(db, org_a, "super-a"))  # staff + superadmin: superadmin_approved
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    assert generate(client, csrf, org_a).status_code == 303
    [proof] = fake.inputs
    assert proof.approval is not None and proof.approval.review_kind == "superadmin_approved"
    html = render_html(proof)
    assert "Approved by Super A (platform administrator; not an agronomist review)" in html
    assert "approved by agronomist" not in html.lower()


def test_cross_org_is_404(
    db: psycopg.Connection, org_a: Org, org_b: Org, tmp_path: Path, fake: FakeRender
) -> None:
    review(db, org_a, org_a.agronomist)
    client_a, csrf_a = client_for(db, org_a.agronomist, tmp_path)
    assert generate(client_a, csrf_a, org_a).status_code == 303
    [(doc_id, _, _)] = documents(db, org_a)
    client_b, csrf_b = client_for(db, org_b.agronomist, tmp_path)
    assert client_b.get(f"/proofs/{doc_id}").status_code == 404
    assert client_b.get(f"/proofs/{doc_id}/download").status_code == 404
    assert generate(client_b, csrf_b, org_a).status_code == 404
    assert client_b.get(f"/plans/{org_a.crop_plan}/proof").status_code == 404


def test_tampered_file_is_not_served(
    db: psycopg.Connection, org_a: Org, tmp_path: Path, fake: FakeRender
) -> None:
    review(db, org_a, org_a.agronomist)
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    assert generate(client, csrf, org_a).status_code == 303
    [(doc_id, _, key)] = documents(db, org_a)
    path = tmp_path / key
    path.chmod(0o640)
    path.write_bytes(path.read_bytes() + b"tampered")
    r = client.get(f"/proofs/{doc_id}/download")
    assert r.status_code == 500 and "does not match the SHA-256" in r.text
    path.unlink()
    r = client.get(f"/proofs/{doc_id}/download")
    assert r.status_code == 500 and "missing from storage" in r.text


def test_store_is_write_once(tmp_path: Path) -> None:
    store = FilesystemProofStore(tmp_path)
    key = f"proof/{UUID(int=1)}/{UUID(int=2)}/{sha256_hex(b'one')}.pdf"
    store.put(key, b"one")
    with pytest.raises(KeyExists):
        store.put(key, b"two")
    assert store.get(key) == b"one"


def test_real_pdf_is_stored_with_its_hash(
    db: psycopg.Connection, org_a: Org, tmp_path: Path
) -> None:
    from cloverproof_app.pdf.render import PdfUnavailable, load_weasyprint

    try:
        load_weasyprint()
    except PdfUnavailable as error:
        if os.environ.get("CP_PDF_TESTS_REQUIRED") == "1":
            pytest.fail(str(error))
        pytest.skip(f"WeasyPrint system libraries unavailable: {error}")
    review(db, org_a, org_a.agronomist)
    client, csrf = client_for(db, org_a.agronomist, tmp_path)
    assert generate(client, csrf, org_a).status_code == 303
    [(doc_id, sha, key)] = documents(db, org_a)
    data = client.get(f"/proofs/{doc_id}/download").content
    assert data.startswith(b"%PDF-") and sha256_hex(data) == sha
    assert (tmp_path / key).read_bytes() == data
