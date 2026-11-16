"""Engine entry point: inputs + already-loaded pack -> Recommendation. Pure."""

from cloverproof_engine import explain
from cloverproof_engine.confidence import assess
from cloverproof_engine.methods import get_method
from cloverproof_engine.models import NutrientForm, RecommendationInput
from cloverproof_engine.pack import Pack
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
    if soil is None:
        pk = Note(code="PK_SOIL_TEST_RECOMMENDED", text=explain.pk_soil_test_recommended())
    else:
        pk = Note(code="PK_NOT_CALCULATED_V0", text=explain.pk_not_calculated_v0())

    notes: list[Note] = []
    if pack.has_placeholders:
        notes.append(
            Note(
                code="PACK_HAS_PLACEHOLDERS",
                text=explain.pack_has_placeholders(pack.id, pack.version),
            )
        )
    if soil is not None and any(v.form is NutrientForm.NO3_N for v in soil.values):
        notes.append(Note(code="SOIL_NITRATE_NOT_USED", text=explain.soil_nitrate_not_used()))

    level, hits = assess(inputs, pack, nitrogen)

    return Recommendation(
        engine_version=ENGINE_VERSION,
        pack_id=pack.id,
        pack_version=pack.version,
        pack_status=pack.status,
        crop=inputs.crop.value,
        nitrogen=nitrogen,
        phosphorus_potassium=pk,
        notes=notes,
        confidence=level,
        confidence_reasons=hits,
        input_snapshot=inputs.model_dump(mode="json"),
    )
