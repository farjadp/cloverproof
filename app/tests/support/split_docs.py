"""Recommendation documents built by the engine from the placeholder test packs, and the
plan page rendered from one without a database. Products are synthetic TEST fixtures."""

from __future__ import annotations

import copy
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from cloverproof_app import planning
from cloverproof_app.db.migrate import REPO_ROOT
from cloverproof_app.line_diff import LineDiff, diff_lines
from cloverproof_app.web import templates
from cloverproof_engine import recommend
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import Crop, RecommendationInput

PACKS = REPO_ROOT / "packs" / "placeholder"
SPLITS = PACKS / "v0.yaml"
NO_SPLITS = PACKS / "v0-no-splits.yaml"
PRODUCT_RULES = PACKS / "v0-product-rules.yaml"
GRANULAR = "TEST FIXTURE granular N 40"
LIQUID = "TEST FIXTURE liquid N 25"
PLAN_ID = UUID("44444444-4444-4444-8444-444444444444")


def product(name: str = GRANULAR, **overrides: Any) -> dict[str, Any]:
    return {
        "id": f"id-{name}", "name": name, "n_pct": 40, "p2o5_pct": 0, "k2o_pct": 0, "s_pct": 0,
        "form": "granular", "grade_source": "TEST label", **overrides,
    }  # fmt: skip


def liquid(**overrides: Any) -> dict[str, Any]:
    return product(LIQUID, n_pct=25, form="liquid", density_kg_per_l=1.25, **overrides)


def sulphur_pack(tmp_dir: Path) -> Path:
    """The product-rules pack, changed to allow sulphur-bearing products."""
    path = tmp_dir / "v0-product-rules-sulphur.yaml"
    text = PRODUCT_RULES.read_text(encoding="utf-8")
    assert "value: exclude" in text
    path.write_text(text.replace("value: exclude", "value: allow"), encoding="utf-8")
    return path


def build(pack: Path = PRODUCT_RULES,
          products: list[dict[str, Any]] | None = None) -> dict[str, Any]:  # fmt: skip
    inputs = RecommendationInput.model_validate(
        {
            "crop": Crop.WHEAT, "target_yield_t_ha": 5.0, "previous_crop": "wheat",
            "area_ha": 10.0, "plan_date": date(2027, 2, 1),
            **({"products": products} if products is not None else {}),
        }
    )  # fmt: skip
    return recommend(inputs, load_pack(pack)).model_dump(mode="json")


def edited(doc: dict[str, Any], rate: str, splits: list[str]) -> dict[str, Any]:
    parsed, errors = planning.parse_edit(doc, rate, splits, "Local trial")
    assert parsed is not None, errors
    return planning.edited_document(doc, parsed, "Local trial")


def rate_only_edit(doc: dict[str, Any], rate: str) -> dict[str, Any]:
    """The N rate changes and the split rows are left as they were: splits are rescaled."""
    return edited(doc, rate, [str(s["rate"]["value"]) for s in doc["nitrogen"]["splits"]])


def old_document() -> dict[str, Any]:
    """A document as engine 0.3 stored it: no timing, line explanation or product keys."""
    doc = copy.deepcopy(build(SPLITS))
    doc["engine_version"] = "0.3.0"
    for split in doc["nitrogen"]["splits"]:
        for key in ("timing_window", "explanation", "product_match"):
            split.pop(key, None)
    doc["nitrogen"]["splits"][0]["fraction"]["value"] = 0.125
    doc["nitrogen"]["splits"][1]["fraction"]["value"] = 0.875
    return doc


def plan_page(doc: dict[str, Any], engine: dict[str, Any] | None = None) -> str:
    """plan.html for `doc`, read-only, with the same context keys as the plan route."""
    field = SimpleNamespace(id=1, name="North 40", farmer_id=2, farmer_name="Test Farmer")
    review = SimpleNamespace(
        decision="approve", reviewer_name="Agro Tester", review_kind="agronomist_approved",
        created_at=datetime(2027, 2, 3, tzinfo=UTC), minutes_spent=7, reason=None,
    )  # fmt: skip
    view = SimpleNamespace(
        number=2 if engine else 1, field=field, plan=SimpleNamespace(id=PLAN_ID),
        status="approved", final_review=review, ai_reviews=[], reviews=[], soil=None,
        read_only=True, latest=SimpleNamespace(id=PLAN_ID),
    )  # fmt: skip
    diff = LineDiff(1, 2, 1, diff_lines(engine, doc)) if engine is not None else None
    limit = SimpleNamespace(value=0.0)
    return templates.get_template("plan.html").render(
        v=view, doc=doc, n_limits=(limit, limit), n_outside_limits=False, line_diff=diff,
        minutes=None, can_review=False, decision_labels={}, ai_decision_labels={},
        reviewer_labels={"agronomist_approved": "Agronomist"}, errors={}, values={},
        status_labels={"approved": "Approved"}, previous_crop_label="Wheat", planning=planning,
        request=SimpleNamespace(url=SimpleNamespace(path="/plans/x")), csrf_token="",
        user=None, org_context=None,
    )  # fmt: skip
