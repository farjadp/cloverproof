"""Engine entry point: inputs + already-loaded pack -> Recommendation. Pure."""

from cloverproof_engine import explain
from cloverproof_engine.confidence import assess
from cloverproof_engine.methods import get_method
from cloverproof_engine.models import (
    NutrientForm,
    RecommendationInput,
    SoilTest,
    SoilTestSource,
)
from cloverproof_engine.pack import Pack, pack_sha256
from cloverproof_engine.results import Note, Recommendation
from cloverproof_engine.version import ENGINE_VERSION


def recommend(inputs: RecommendationInput, pack: Pack) -> Recommendation:
    crop_cfg = pack.crops.get(inputs.crop)
    if crop_cfg is None:
        raise ValueError(f"pack {pack.id} {pack.version} has no config for {inputs.crop.value}")

    method = get_method(crop_cfg.nitrogen.method)
    if method.nutrient != "N":
        raise ValueError(f"method {method.method_id!r} is not a nitrogen method")
    nitrogen = method.calculate(inputs, pack)

    soil = inputs.soil_test
    pk = _pk_note(soil)

    notes: list[Note] = []
    if pack.has_placeholders:
        notes.append(
            Note(
                code="PACK_HAS_PLACEHOLDERS",
                text=explain.pack_has_placeholders(pack.id, pack.version),
            )
        )
    if soil is not None and any(v.form is NutrientForm.NO3_N for v in soil.values):
        notes.append(
            Note(
                code="SOIL_NITRATE_NOT_USED", text=explain.soil_nitrate_not_used(nitrogen.method_id)
            )
        )

    level, hits = assess(inputs, pack, nitrogen)

    return Recommendation(
        engine_version=ENGINE_VERSION,
        pack_id=pack.id,
        pack_version=pack.version,
        pack_status=pack.status,
        pack_sha256=pack_sha256(pack),
        crop=inputs.crop.value,
        nitrogen=nitrogen,
        phosphorus_potassium=pk,
        notes=notes,
        confidence=level,
        confidence_reasons=hits,
        input_snapshot=inputs.model_dump(mode="json"),
    )


def _pk_note(soil: SoilTest | None) -> Note:
    """Only a lab test with a P or K value counts as a P/K soil test.

    No test, an estimate, or a lab test without P and K -> recommend a soil test.
    """
    if soil is None:
        reason: explain.PkTestMissing = "no_test"
    elif soil.source is SoilTestSource.ESTIMATE:
        reason = "estimate"
    elif soil.value_for("P") is None and soil.value_for("K") is None:
        reason = "no_p_or_k_value"
    else:
        return Note(code="PK_NOT_CALCULATED_V0", text=explain.pk_not_calculated_v0())
    return Note(code="PK_SOIL_TEST_RECOMMENDED", text=explain.pk_soil_test_recommended(reason))
