"""Proof PDF v0: required sections, an explanation for every number, wording rules,
placeholder markers, approval line (D4 hook), deterministic bytes.

HTML checks always run (the HTML is exactly what WeasyPrint renders). PDF checks need
WeasyPrint's system libraries (pango); text extraction from the PDF also needs pypdf.
Both are skipped when missing, unless CP_PDF_TESTS_REQUIRED=1.
"""

from __future__ import annotations

import copy
import html
import io
import os
import re
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest

from cloverproof_app.db.migrate import REPO_ROOT
from cloverproof_app.pdf import (
    AGRONOMIST_APPROVED,
    AI_REVIEWED,
    FORBIDDEN_PHRASES,
    NO_SOIL_TEST,
    PLACEHOLDER_BANNER,
    SUPERADMIN_APPROVED,
    Approval,
    Comparison,
    NotAnApproval,
    ProofInput,
    approval_line,
    render_html,
)
from cloverproof_app.storage import sha256_hex
from cloverproof_engine import recommend
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import (
    ConcentrationUnit,
    Crop,
    ExtractionMethod,
    NutrientForm,
    RecommendationInput,
    SoilTest,
    SoilTestSource,
    SoilTestValue,
)

PACK = load_pack(REPO_ROOT / "packs" / "placeholder" / "v0.yaml")
DOC_ID = UUID("11111111-1111-4111-8111-111111111111")
REC_ID = UUID("22222222-2222-4222-8222-222222222222")
APPROVED_AT = datetime(2027, 2, 3, 14, 30, tzinfo=UTC)
REQUIRED = "CP_PDF_TESTS_REQUIRED"


def engine_doc(with_soil: bool = True) -> dict[str, Any]:
    soil = SoilTest(
        sample_date=date(2026, 10, 1),
        depth_top_cm=0,
        depth_bottom_cm=15,
        source=SoilTestSource.LAB,
        lab="Test Lab",
        values=[
            SoilTestValue(form=NutrientForm.P2O5, value=12, unit=ConcentrationUnit.MG_PER_KG,
                          extraction_method=ExtractionMethod.OLSEN),
            SoilTestValue(form=NutrientForm.K, value=150, unit=ConcentrationUnit.PPM,
                          extraction_method=ExtractionMethod.OTHER,
                          extraction_method_detail="Ammonium acetate"),
        ],
    )  # fmt: skip
    inputs = RecommendationInput(
        crop=Crop.WHEAT,
        target_yield_t_ha=6.0,
        previous_crop="canola",
        area_ha=12.5,
        plan_date=date(2027, 3, 1),
        soil_test=soil if with_soil else None,
    )
    return recommend(inputs, PACK).model_dump(mode="json")


def proof(doc: dict[str, Any] | None = None, approval: Approval | None = None,
          document_id: UUID = DOC_ID, **overrides: Any) -> ProofInput:  # fmt: skip
    values: dict[str, Any] = {
        "document_id": document_id,
        "recommendation_id": REC_ID,
        "version_number": 1,
        "farmer_name": "Test Farmer",
        "farm_name": "Home Farm",
        "field_name": "North 40",
        "season_label": "2026-2027",
        "previous_crop_label": "Canola",
        "doc": doc if doc is not None else engine_doc(),
        "approval": approval
        if approval is not None
        else Approval("Agro Tester", APPROVED_AT, AGRONOMIST_APPROVED),
    }
    values.update(overrides)
    return ProofInput(**values)


def validated(doc: dict[str, Any]) -> dict[str, Any]:
    """The same document as if it came from a validated pack (no placeholders)."""
    new = copy.deepcopy(doc)
    new["pack_status"] = "validated"
    for number in explained_numbers(new):
        number["uses_placeholder"] = False
    for constant in new["nitrogen"]["constants_used"]:
        constant["status"] = "VALIDATED"
        constant["source"] = "Fixture source"
    return new


def explained_numbers(doc: dict[str, Any]) -> Iterator[dict[str, Any]]:
    n = doc["nitrogen"]
    yield n["rate"]
    yield n["total"]
    yield from n["components"]
    for split in n["splits"]:
        yield split["fraction"]
        yield split["rate"]
        yield split["total"]


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def visible_text(markup: str) -> str:
    """The document's visible text: no <style>, no tags, entities decoded."""
    body = re.sub(r"<style.*?</style>", " ", markup, flags=re.S)
    return squash(html.unescape(re.sub(r"<[^>]+>", " ", body)))


def assert_wording(text: str) -> None:
    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in lowered, phrase
    # "approved by" only inside our own reviewer lines (see approval_line).
    allowed = (
        "reviewed and approved by agronomist agro tester",
        "approved by agro tester (platform administrator; not an agronomist review)",
    )
    for match in re.finditer(r"approved by", lowered):
        window = lowered[max(0, match.start() - 13) :]
        assert any(
            window.startswith(a) or lowered[match.start() :].startswith(a) for a in allowed
        ), lowered[match.start() - 20 : match.end() + 40]


# --- HTML (always runs) -----------------------------------------------------------------


def test_required_sections_present() -> None:
    text = visible_text(render_html(proof()))
    for heading in (
        "Farm and field", "Inputs", "Soil test", "Recommendation",
        "How the engine calculated the rate", "Split applications and timing", "Confidence",
        "Phosphorus and potassium", "Constants used", "Versions and identifiers",
        "This file",
    ):  # fmt: skip
        assert heading in text, heading
    for value in ("Test Farmer", "Home Farm", "North 40", "12.5 ha", "Wheat", "6 t/ha",
                  "Canola", "2027-03-01", "2026-2027", str(DOC_ID), str(REC_ID)):  # fmt: skip
        assert value in text, value


def test_every_number_has_its_explanation_line() -> None:
    doc = engine_doc()
    text = visible_text(render_html(proof(doc)))
    numbers = list(explained_numbers(doc))
    assert len(numbers) >= 8
    for number in numbers:
        assert number["explanation"]
        assert squash(number["explanation"]) in text, number["name"]
    assert "No explanation recorded" not in text


def test_missing_explanation_is_visible_not_silent() -> None:
    doc = engine_doc()
    doc["nitrogen"]["total"]["explanation"] = ""
    assert "No explanation recorded" in visible_text(render_html(proof(doc)))


def test_split_timing_label_comes_from_the_pack() -> None:
    doc = engine_doc()
    text = visible_text(render_html(proof(doc)))
    for split in doc["nitrogen"]["splits"]:
        assert split["stage_label"] in text


def test_soil_test_method_depth_date_form_units() -> None:
    text = visible_text(render_html(proof()))
    for value in ("2026-10-01", "0\u201315 cm", "Lab (Test Lab)", "P2O5", "Olsen", "mg/kg",
                  "ppm", "Other: Ammonium acetate", "12", "150"):  # fmt: skip
        assert value in text, value


def test_ammonium_acetate_method_has_its_label() -> None:
    """S1-exit D2: the PDF used to print the raw key "ammonium-acetate"."""
    doc = engine_doc()
    values = doc["input_snapshot"]["soil_test"]["values"]
    values[1]["extraction_method"] = "ammonium-acetate"
    values[1]["extraction_method_detail"] = None
    text = visible_text(render_html(proof(doc)))
    assert "Ammonium acetate" in text
    assert "ammonium-acetate" not in text


def test_pdf_and_app_method_labels_are_one_table() -> None:
    from cloverproof_app import planning
    from cloverproof_app.pdf import render as pdf_render

    assert pdf_render.METHOD_LABELS is planning.METHOD_LABELS
    assert {m.value for m in ExtractionMethod} <= set(pdf_render.METHOD_LABELS)


def test_no_soil_test_says_so_and_asks_for_p_k_test() -> None:
    text = visible_text(render_html(proof(engine_doc(with_soil=False))))
    assert NO_SOIL_TEST == "No soil test: N only; P/K soil test recommended"
    assert NO_SOIL_TEST in text
    assert "Olsen" not in text


def test_confidence_and_reasons() -> None:
    doc = engine_doc(with_soil=False)
    text = visible_text(render_html(proof(doc)))
    assert f"{doc['confidence'].capitalize()} confidence" in text
    for reason in doc["confidence_reasons"]:
        assert squash(reason["reason"]) in text
        assert reason["rule_id"] in text


def test_placeholder_pack_banner_and_markers() -> None:
    doc = engine_doc()
    assert doc["pack_status"] == "placeholder"
    markup = render_html(proof(doc))
    text = visible_text(markup)
    assert PLACEHOLDER_BANNER == "PLACEHOLDER values — not for field use"
    assert PLACEHOLDER_BANNER in text
    assert PLACEHOLDER_BANNER in markup.split("<body", 1)[0]  # also on every page (CSS)
    assert "PLACEHOLDER — not yet validated" in text


def test_validated_pack_has_no_placeholder_banner_or_markers() -> None:
    markup = render_html(proof(validated(engine_doc())))
    assert PLACEHOLDER_BANNER not in markup
    assert "not yet validated" not in visible_text(markup)


def test_pack_and_engine_provenance() -> None:
    doc = engine_doc()
    text = visible_text(render_html(proof(doc)))
    for value in (doc["engine_version"], doc["pack_id"], doc["pack_version"], doc["pack_sha256"]):
        assert value in text


def test_hash_statement_and_how_to_check() -> None:
    text = visible_text(render_html(proof()))
    assert "SHA-256 of this file is recorded in CloverProof" in text
    assert "cannot contain its own SHA-256" in text


SUPERADMIN = Approval("Agro Tester", APPROVED_AT, SUPERADMIN_APPROVED)


@pytest.mark.parametrize("pack_status", ["placeholder", "validated"])
def test_no_third_party_or_certification_wording(pack_status: str) -> None:
    doc = engine_doc() if pack_status == "placeholder" else validated(engine_doc())
    draft = ProofInput(**{**proof(doc).__dict__, "approval": None})
    for item in (proof(doc), proof(doc, approval=SUPERADMIN), draft):
        assert_wording(visible_text(render_html(item)))


def test_agronomist_approval_line() -> None:
    approval = Approval("Agro Tester", APPROVED_AT, AGRONOMIST_APPROVED)
    assert approval_line(approval) == "Reviewed and approved by agronomist Agro Tester"
    markup = render_html(proof(approval=approval))
    text = visible_text(markup)
    assert "Reviewed and approved by agronomist Agro Tester" in text
    assert "2027-02-03 14:30 UTC" in text and "agronomist_approved" in text
    assert ">DRAFT<" not in markup and "platform administrator" not in text


def test_superadmin_approval_is_not_called_an_agronomist_review() -> None:
    line = approval_line(SUPERADMIN)
    assert line == "Approved by Agro Tester (platform administrator; not an agronomist review)"
    text = visible_text(render_html(proof(approval=SUPERADMIN)))
    assert line in text and "superadmin_approved" in text
    assert "approved by agronomist" not in text.lower()


def test_ai_review_is_never_an_approval() -> None:
    with pytest.raises(NotAnApproval):
        Approval("cp-agronomist", APPROVED_AT, AI_REVIEWED)
    with pytest.raises(NotAnApproval):
        Approval("someone", APPROVED_AT, "robot")


def test_draft_watermark_without_approval() -> None:
    draft = ProofInput(**{**proof().__dict__, "approval": None})
    markup = render_html(draft)
    text = visible_text(markup)
    assert "DRAFT" in text and "Not approved" in text
    assert "approved by" not in text.lower()
    assert "DRAFT — not approved" in markup.split("<body", 1)[0]  # every page (CSS)


def test_engine_vs_final_and_lineage() -> None:
    doc = engine_doc()
    engine = doc["nitrogen"]["rate"]
    final = {**engine, "value": engine["value"] - 10, "explanation": "Agronomist lowered it."}
    item = proof(doc, comparison=(Comparison("N rate", engine, final),), version_number=2)
    text = visible_text(render_html(item))
    assert "Engine vs final" in text and "Agronomist lowered it." in text
    assert "Input snapshot SHA-256" in text and item.input_snapshot_sha256 in text


def test_user_text_is_escaped() -> None:
    markup = render_html(proof(field_name="<script>x</script>"))
    assert "<script>" not in markup and "&lt;script&gt;" in markup


# --- PDF (needs pango; text checks need pypdf) ------------------------------------------


def _skip(reason: str) -> None:
    if os.environ.get(REQUIRED) == "1":
        pytest.fail(reason)
    pytest.skip(reason)


@pytest.fixture(scope="module")
def render_pdf() -> Any:
    try:
        from cloverproof_app.pdf import render_pdf as render
        from cloverproof_app.pdf.render import load_weasyprint

        load_weasyprint()
    except Exception as error:  # OSError when pango/gobject cannot be loaded
        _skip(f"WeasyPrint system libraries unavailable ({error.__class__.__name__})")
    return render


def pdf_reader(data: bytes) -> Any:
    try:
        import pypdf  # type: ignore[import-not-found]
    except ImportError:
        # pypdf is not a dependency (only weasyprint is approved): always a plain skip.
        pytest.skip("pypdf not installed (optional PDF text extraction)")
    return pypdf.PdfReader(io.BytesIO(data))


def compact(text: str) -> str:
    """No whitespace at all: PDF line breaks fall anywhere (also after "-")."""
    return re.sub(r"\s+", "", text)


def pdf_text(data: bytes) -> str:
    return squash(" ".join(page.extract_text() or "" for page in pdf_reader(data).pages))


def test_pdf_builds(render_pdf: Any) -> None:
    data = render_pdf(proof())
    assert data.startswith(b"%PDF-")
    assert data.rstrip().endswith(b"%%EOF")


def test_pdf_is_a4(render_pdf: Any) -> None:
    for page in pdf_reader(render_pdf(proof())).pages:
        assert (round(float(page.mediabox.width)), round(float(page.mediabox.height))) == (595, 842)


def test_pdf_hash_is_stable_for_identical_inputs(render_pdf: Any) -> None:
    first = render_pdf(proof())
    time.sleep(1.1)  # cross a second: font timestamps once leaked into the bytes
    second = render_pdf(proof())
    assert sha256_hex(first) == sha256_hex(second)
    other = render_pdf(proof(document_id=UUID("33333333-3333-4333-8333-333333333333")))
    assert sha256_hex(other) != sha256_hex(first)


def test_pdf_has_no_creation_timestamp(render_pdf: Any) -> None:
    data = render_pdf(proof())
    assert b"/CreationDate" not in data and b"/ModDate" not in data


def test_pdf_text_explanations_banner_wording(render_pdf: Any) -> None:
    doc = engine_doc()
    text = pdf_text(render_pdf(proof(doc)))
    flat = compact(text)
    for number in explained_numbers(doc):
        assert compact(number["explanation"]) in flat, number["name"]
    for needle in (PLACEHOLDER_BANNER, "Reviewed and approved by agronomist Agro Tester",
                   "SHA-256 of this file is recorded in CloverProof",
                   "not yet validated"):  # fmt: skip
        assert compact(needle) in flat, needle
    assert_wording(text)
