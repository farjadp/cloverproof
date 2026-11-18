"""Engine entry point: inputs + already-loaded pack -> Recommendation. Pure."""

from cloverproof_engine import explain
from cloverproof_engine.confidence import assess
from cloverproof_engine.methods import get_method
from cloverproof_engine.models import (
    NutrientForm,
    RecommendationInput,
    SoilEstimate,
    SoilEstimateValue,
    SoilTest,
    SoilTestSource,
)
from cloverproof_engine.pack import Pack, pack_sha256
from cloverproof_engine.products import match_products
from cloverproof_engine.results import (
    ExplainedNumber,
    Note,
    PkRefused,
    PkResults,
    Recommendation,
    SoilEstimateContext,
    SoilEstimateLine,
)
from cloverproof_engine.version import ENGINE_VERSION


def recommend(inputs: RecommendationInput, pack: Pack) -> Recommendation:
    crop_cfg = pack.crops.get(inputs.crop)
    if crop_cfg is None:
        raise ValueError(f"pack {pack.id} {pack.version} has no config for {inputs.crop.value}")

    method = get_method(crop_cfg.nitrogen.method)
    if method.nutrient != "N":
        raise ValueError(f"method {method.method_id!r} is not a nitrogen method")
    nitrogen = match_products(inputs, pack, method.calculate(inputs, pack))

    soil = inputs.soil_test
    pk, pk_rates = _phosphorus_potassium(inputs, pack)

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

    level, hits = assess(inputs, pack, nitrogen, pk_rates)

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
        phosphorus_potassium_rates=pk_rates,
        soil_estimate=_soil_estimate_context(inputs),
    )


def _soil_estimate_context(inputs: RecommendationInput) -> SoilEstimateContext | None:
    """The estimate as labelled context. Nothing else in the engine reads it.

    TODO(agronomist): should an estimate adjust the N rate or the confidence, and how?
    No pack rule says so, so it does neither (docs/agronomist-todo.md #51).
    """
    estimate = inputs.soil_estimate
    if estimate is None:
        return None
    soil = inputs.soil_test
    lab_test_given = soil is not None and soil.source is SoilTestSource.LAB
    return SoilEstimateContext(
        source=estimate.provider,
        version=estimate.version,
        attribution=estimate.attribution,
        citation=estimate.citation,
        lab_test_given=lab_test_given,
        values=[_soil_estimate_line(estimate, value) for value in estimate.values],
        explanation=explain.soil_estimate_context(
            estimate.provider, estimate.version, lab_test_given
        ),
    )


def _soil_estimate_line(estimate: SoilEstimate, item: SoilEstimateValue) -> SoilEstimateLine:
    def number(name: str, value: float, unit: str, explanation: str) -> ExplainedNumber:
        # Read from the input, not from a pack: no pack constant feeds it.
        return ExplainedNumber(
            name=name, value=value, unit=unit, explanation=explanation, uses_placeholder=False
        )

    prop, depth, unit = item.property, item.depth, item.unit
    q05, q95, ratio = item.q05, item.q95, item.uncertainty_ratio
    return SoilEstimateLine(
        property=prop,
        depth=depth,
        value=number(
            explain.soil_estimate_name(prop),
            item.value,
            unit,
            explain.soil_estimate_value(
                prop,
                depth,
                item.value,
                unit,
                estimate.provider,
                estimate.version,
                item.resolution_m,
                item.retrieved_on,
            ),
        ),
        q05=None
        if q05 is None
        else number(
            explain.soil_estimate_lower_name(prop),
            q05,
            unit,
            explain.soil_estimate_range(prop, depth, "Lower end (Q0.05)"),
        ),
        q95=None
        if q95 is None
        else number(
            explain.soil_estimate_upper_name(prop),
            q95,
            unit,
            explain.soil_estimate_range(prop, depth, "Upper end (Q0.95)"),
        ),
        uncertainty_ratio=None
        if ratio is None
        else number(
            explain.soil_estimate_uncertainty_name(prop),
            ratio,
            "ratio",
            explain.soil_estimate_uncertainty(prop, depth),
        ),
        source=estimate.provider,
        version=estimate.version,
        resolution_m=item.resolution_m,
        retrieved_on=item.retrieved_on,
        attribution=estimate.attribution,
    )


def _phosphorus_potassium(inputs: RecommendationInput, pack: Pack) -> tuple[Note, PkResults | None]:
    """The P/K note, plus rates when a lab test meets a pack with P/K tables (rule 3)."""
    note = _pk_note(inputs.soil_test)
    cfg = pack.crops[inputs.crop].phosphorus_potassium
    if cfg is None or note.code != "PK_NOT_CALCULATED_V0":
        return note, None
    method = get_method(cfg.method)
    if method.nutrient != "PK":
        raise ValueError(f"method {method.method_id!r} is not a P/K method")
    rates: PkResults = method.calculate(inputs, pack)
    refusals = [line.explanation for line in rates.lines if isinstance(line, PkRefused)]
    if len(refusals) == len(rates.lines):
        return Note(
            code="PK_NOT_CALCULATED_LAB_TEST", text=explain.pk_lab_test_no_rate(refusals)
        ), rates
    return Note(code="PK_FROM_LAB_TEST", text=explain.pk_from_lab_test(refusals)), rates


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
