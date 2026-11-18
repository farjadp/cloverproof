"""P and K from a lab soil test, read from the pack table for the value's own method."""

import copy
import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from cloverproof_engine import recommend, units
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.golden import ExpectedCase, compare, parse_golden_case
from cloverproof_engine.loaders import load_golden_case, load_pack
from cloverproof_engine.methods import MissingInputError, OutOfScopeError, get_method
from cloverproof_engine.models import NutrientForm, RecommendationInput, SoilTest
from cloverproof_engine.pack import Pack, parse_pack
from cloverproof_engine.results import ExplainedNumber, PkRecommended, PkRefused, Recommendation

REPO_ROOT = Path(__file__).resolve().parents[2]
CA_ON_PATH = REPO_ROOT / "packs" / "ca-on" / "v2.yaml"
GOLDEN_DIR = REPO_ROOT / "engine" / "tests" / "golden"

OLSEN_P = {"form": "P", "value": 7, "unit": "mg/kg", "extraction_method": "olsen"}
ACETATE_K = {"form": "K", "value": 40, "unit": "mg/kg", "extraction_method": "ammonium-acetate"}


@pytest.fixture
def pack() -> Pack:
    return load_pack(CA_ON_PATH)


def _soil(*values: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return {
        "sample_date": "2026-09-15",
        "depth_top_cm": 0,
        "depth_bottom_cm": 15,
        "source": "lab",
        "lab": "TEST FIXTURE lab",
        "values": list(values),
        **overrides,
    }


def _input(soil: dict[str, Any] | None) -> RecommendationInput:
    return RecommendationInput.model_validate(
        {
            "crop": "wheat",
            "target_yield_t_ha": 6.0,
            "previous_crop": "corn",
            "area_ha": 20.0,
            "plan_date": date(2027, 3, 15),
            "n_price": {
                "n_price_per_kg_n": 1.5,
                "grain_price_per_kg": 0.25,
                "currency": "CAD",
                "source": "TEST FIXTURE",
                "price_date": "2027-01-20",
            },
            "wheat_class": "pastry",
            "manure_applied": False,
            "soil_test": soil,
        }
    )


def _run(pack: Pack, *values: dict[str, Any], **soil: Any) -> Recommendation:
    return recommend(_input(_soil(*values, **soil)), pack)


def _recommended(line: PkRecommended | PkRefused) -> PkRecommended:
    assert isinstance(line, PkRecommended), line
    return line


def _refused(line: PkRecommended | PkRefused) -> PkRefused:
    assert isinstance(line, PkRefused), line
    return line


def _numbers(node: Any) -> Iterator[ExplainedNumber]:
    if isinstance(node, ExplainedNumber):
        yield node
    elif hasattr(type(node), "model_fields"):
        for name in type(node).model_fields:
            yield from _numbers(getattr(node, name))


def test_olsen_p_and_acetate_k_read_their_own_tables(pack: Pack) -> None:
    rec = _run(pack, OLSEN_P, ACETATE_K)
    assert rec.phosphorus_potassium.code == "PK_FROM_LAB_TEST"
    assert rec.phosphorus_potassium_rates is not None
    p = _recommended(rec.phosphorus_potassium_rates.phosphorus)
    k = _recommended(rec.phosphorus_potassium_rates.potassium)
    assert (p.method_id, p.extraction_method.value) == ("pk_soil_test_table", "olsen")
    assert k.extraction_method.value == "ammonium-acetate"
    assert (p.table_band, p.response) == ("6-7 ppm", "HR")
    assert p.response_label == "high response"
    assert p.rate_oxide.amount.value == 50
    assert k.rate_oxide.amount.value == 30


def test_both_forms_are_shown_and_explicit(pack: Pack) -> None:
    rates = _run(pack, OLSEN_P, ACETATE_K).phosphorus_potassium_rates
    assert rates is not None
    p = _recommended(rates.phosphorus)
    k = _recommended(rates.potassium)
    assert p.rate_form is NutrientForm.P2O5
    assert (p.rate_oxide.form, p.rate_elemental.form) == (NutrientForm.P2O5, NutrientForm.P)
    assert (k.rate_oxide.form, k.rate_elemental.form) == (NutrientForm.K2O, NutrientForm.K)
    assert (p.rate_oxide.amount.unit, p.rate_elemental.amount.unit) == ("kg P2O5/ha", "kg P/ha")
    assert (k.total_oxide.amount.unit, k.total_elemental.amount.unit) == ("kg K2O", "kg K")
    assert p.soil_test_elemental.amount.unit == "mg P/kg"
    assert p.soil_test_oxide.amount.unit == "mg P2O5/kg"
    assert p.rate_elemental.amount.value == pytest.approx(units.p2o5_to_p(50))
    assert p.soil_test_oxide.amount.value == pytest.approx(units.p_to_p2o5(7))
    assert k.rate_elemental.amount.value == pytest.approx(units.k2o_to_k(30))
    assert p.total_oxide.amount.value == pytest.approx(50 * 20)
    assert k.total_elemental.amount.value == pytest.approx(units.k2o_to_k(30) * 20)


def test_oxide_input_is_converted_before_the_table(pack: Pack) -> None:
    rates = _run(
        pack,
        {**OLSEN_P, "form": "P2O5", "value": units.p_to_p2o5(7)},
        {**ACETATE_K, "form": "K2O", "value": units.k_to_k2o(40)},
    ).phosphorus_potassium_rates
    assert rates is not None
    p = _recommended(rates.phosphorus)
    k = _recommended(rates.potassium)
    assert p.soil_test_elemental.amount.value == pytest.approx(7)
    assert (p.table_band, p.rate_oxide.amount.value) == ("6-7 ppm", 50)
    assert (k.table_band, k.rate_oxide.amount.value) == ("31-45 ppm", 30)
    assert "as reported" in p.soil_test_oxide.amount.explanation
    assert "converted" in p.soil_test_elemental.amount.explanation


@pytest.mark.parametrize("element", [4.0, 6.0, 8.0, 10.0, 13.0, 16.0, 21.0, 26.0, 31.0, 41.0, 61.0])
def test_an_oxide_value_on_a_band_edge_stays_in_that_band(pack: Pack, element: float) -> None:
    oxide = {**OLSEN_P, "form": "P2O5", "value": units.p_to_p2o5(element)}
    from_oxide = _run(pack, oxide).phosphorus_potassium_rates
    direct = _run(pack, {**OLSEN_P, "value": element}).phosphorus_potassium_rates
    assert from_oxide is not None and direct is not None
    band = _recommended(from_oxide.phosphorus).table_band
    assert band == _recommended(direct.phosphorus).table_band


def test_ppm_and_mg_per_kg_read_the_same_band(pack: Pack) -> None:
    rates = _run(pack, {**OLSEN_P, "unit": "ppm"}).phosphorus_potassium_rates
    assert rates is not None
    assert _recommended(rates.phosphorus).table_band == "6-7 ppm"


def test_value_between_printed_bands_takes_the_lower_band_and_says_so(pack: Pack) -> None:
    rates = _run(pack, {**OLSEN_P, "value": 7.5}).phosphorus_potassium_rates
    assert rates is not None
    p = _recommended(rates.phosphorus)
    assert (p.table_band, p.rate_oxide.amount.value) == ("6-7 ppm", 50)
    assert "engine choice" in p.rate_oxide.amount.explanation
    assert "no interpolation" in p.rate_oxide.amount.explanation


def test_top_open_band_covers_every_higher_value_and_carries_the_warning(pack: Pack) -> None:
    rates = _run(pack, {**OLSEN_P, "value": 500}).phosphorus_potassium_rates
    assert rates is not None
    p = _recommended(rates.phosphorus)
    assert (p.table_band, p.response, p.rate_oxide.amount.value) == ("61+ ppm", "NR", 0)
    assert "may reduce crop yield or quality" in p.rate_oxide.amount.explanation


def test_rate_explanation_cites_the_table_and_its_assumptions(pack: Pack) -> None:
    rates = _run(pack, OLSEN_P).phosphorus_potassium_rates
    assert rates is not None
    text = _recommended(rates.phosphorus).rate_oxide.amount.explanation
    assert "PLACEHOLDER" in text
    assert "Table 4-20" in text
    assert "seeded down" in text
    assert "manure" in text


@pytest.mark.parametrize("method", ["mehlich-3", "bray-1", "ammonium-acetate"])
def test_p_from_another_method_never_reads_the_olsen_table(pack: Pack, method: str) -> None:
    rates = _run(pack, {**OLSEN_P, "extraction_method": method}).phosphorus_potassium_rates
    assert rates is not None
    line = _refused(rates.phosphorus)
    assert line.code == "no_table_for_method"
    assert method in line.explanation
    assert "olsen" in line.explanation


@pytest.mark.parametrize("method", ["mehlich-3", "olsen", "bray-1"])
def test_k_from_another_method_never_reads_the_acetate_table(pack: Pack, method: str) -> None:
    rates = _run(pack, {**ACETATE_K, "extraction_method": method}).phosphorus_potassium_rates
    assert rates is not None
    line = _refused(rates.potassium)
    assert line.code == "no_table_for_method"
    assert "ammonium-acetate" in line.explanation


def test_method_other_is_refused_and_named(pack: Pack) -> None:
    value = {**OLSEN_P, "extraction_method": "other", "extraction_method_detail": "Kelowna"}
    rates = _run(pack, value).phosphorus_potassium_rates
    assert rates is not None
    line = _refused(rates.phosphorus)
    assert line.code == "no_table_for_method"
    assert "Kelowna" in line.explanation


def test_missing_method_is_refused_and_the_other_nutrient_still_runs(pack: Pack) -> None:
    rec = _run(pack, {**OLSEN_P, "extraction_method": None}, ACETATE_K)
    assert rec.phosphorus_potassium_rates is not None
    line = _refused(rec.phosphorus_potassium_rates.phosphorus)
    assert line.code == "no_extraction_method"
    assert "extraction method" in line.explanation
    _recommended(rec.phosphorus_potassium_rates.potassium)
    assert rec.phosphorus_potassium.code == "PK_FROM_LAB_TEST"
    assert line.explanation in rec.phosphorus_potassium.text


def test_missing_k_value_is_refused_by_name(pack: Pack) -> None:
    rates = _run(pack, OLSEN_P).phosphorus_potassium_rates
    assert rates is not None
    line = _refused(rates.potassium)
    assert line.code == "no_soil_test_value"
    assert "potassium" in line.explanation.lower()


def test_all_refused_has_its_own_note_with_every_reason(pack: Pack) -> None:
    rec = _run(
        pack,
        {**OLSEN_P, "extraction_method": "mehlich-3"},
        {**ACETATE_K, "extraction_method": None},
    )
    note = rec.phosphorus_potassium
    assert note.code == "PK_NOT_CALCULATED_LAB_TEST"
    rates = rec.phosphorus_potassium_rates
    assert rates is not None
    for line in (rates.phosphorus, rates.potassium):
        assert _refused(line).explanation in note.text


@pytest.mark.parametrize(("top", "bottom"), [(0, 30), (0, 10), (5, 15)])
def test_other_sampling_depth_is_refused(pack: Pack, top: float, bottom: float) -> None:
    rates = _run(
        pack, OLSEN_P, ACETATE_K, depth_top_cm=top, depth_bottom_cm=bottom
    ).phosphorus_potassium_rates
    assert rates is not None
    for line in (rates.phosphorus, rates.potassium):
        refused = _refused(line)
        assert refused.code == "sample_depth_mismatch"
        assert "15" in refused.explanation


def test_stale_test_keeps_the_rate_and_fires_the_existing_rule(pack: Pack) -> None:
    rec = _run(pack, OLSEN_P, sample_date="2020-09-15")
    assert rec.phosphorus_potassium_rates is not None
    _recommended(rec.phosphorus_potassium_rates.phosphorus)
    assert "C3_SOIL_TEST_STALE" in [h.rule_id for h in rec.confidence_reasons]


def test_no_soil_test_gives_no_pk_result(pack: Pack) -> None:
    rec = recommend(_input(None), pack)
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"
    assert rec.phosphorus_potassium_rates is None
    assert "phosphorus_potassium_rates" not in rec.model_dump(mode="json")
    assert rec.confidence <= Confidence.MEDIUM


def test_estimate_never_gives_a_rate(pack: Pack) -> None:
    rec = _run(pack, OLSEN_P, ACETATE_K, source="estimate")
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"
    assert rec.phosphorus_potassium_rates is None


@pytest.mark.parametrize("soil", [None, _soil(OLSEN_P, ACETATE_K, source="estimate")])
def test_the_method_itself_refuses_without_a_lab_test(pack: Pack, soil: Any) -> None:
    rates = get_method("pk_soil_test_table").calculate(_input(soil), pack)
    assert _refused(rates.phosphorus).code == "no_lab_test"
    assert _refused(rates.potassium).code == "no_lab_test"


def test_the_pk_config_accepts_only_a_pk_method(pack: Pack) -> None:
    data = pack.model_dump(mode="json")
    data["crops"]["wheat"]["phosphorus_potassium"]["method"] = "n_mass_balance"
    with pytest.raises(ValueError, match="pk_soil_test_table"):
        parse_pack(data)


def test_placeholder_tables_are_listed_and_force_low(pack: Pack) -> None:
    rec = _run(pack, OLSEN_P, ACETATE_K)
    assert rec.confidence is Confidence.LOW
    reason = next(h for h in rec.confidence_reasons if h.rule_id.startswith("C6_PLACEHOLDER"))
    assert "phosphorus_potassium.nutrients.P.tables.olsen.bands[2].rate" in reason.reason
    assert "phosphorus_potassium.nutrients.K.tables.ammonium-acetate.bands[2].rate" in reason.reason
    assert "phosphorus_potassium.sample_depth_cm" in reason.reason


def test_refused_nutrients_add_no_placeholder_paths(pack: Pack) -> None:
    rec = _run(pack, {**OLSEN_P, "extraction_method": "bray-1"})
    assert "phosphorus_potassium" not in " ".join(h.reason for h in rec.confidence_reasons)


def test_every_pk_number_is_explained_and_flagged(pack: Pack) -> None:
    rates = _run(pack, OLSEN_P, ACETATE_K).phosphorus_potassium_rates
    assert rates is not None
    for line in (rates.phosphorus, rates.potassium):
        recommended = _recommended(line)
        numbers = list(_numbers(recommended))
        assert len(numbers) == 6
        assert all(n.explanation.strip() for n in numbers)
        assert all(n.uses_placeholder for n in numbers if n.unit.startswith("kg "))
        assert not any(n.uses_placeholder for n in numbers if n.unit.startswith("mg "))
        assert recommended.constants_used


def test_note_text_quotes_no_rate(pack: Pack) -> None:
    text = _run(pack, OLSEN_P, ACETATE_K).phosphorus_potassium.text
    assert "kg P2O5" not in text
    assert "kg K2O" not in text
    assert "the agronomist decides P and K" in text


def test_manure_applied_gives_no_p_or_k_result(pack: Pack) -> None:
    inputs = _input(_soil(OLSEN_P, ACETATE_K)).model_copy(update={"manure_applied": True})
    with pytest.raises(OutOfScopeError, match="manure"):
        recommend(inputs, pack)


def test_manure_not_answered_gives_no_p_or_k_result(pack: Pack) -> None:
    inputs = _input(_soil(OLSEN_P, ACETATE_K)).model_copy(update={"manure_applied": None})
    with pytest.raises(MissingInputError, match="manure_applied"):
        recommend(inputs, pack)


NITROGEN_ONLY_NOTE = (
    "This plan covers nitrogen only: it has no P or K rate. The engine checked the lab soil "
    "test against the pack's P and K tables, but those results are unreviewed, are not shown "
    "and are not part of this plan; the agronomist decides P and K from the soil test."
)


def test_note_says_the_plan_is_nitrogen_only(pack: Pack) -> None:
    assert _run(pack, OLSEN_P, ACETATE_K).phosphorus_potassium.text == NITROGEN_ONLY_NOTE


def test_a_refusal_does_not_imply_the_other_nutrient_has_a_shown_rate(pack: Pack) -> None:
    note = _run(pack, OLSEN_P, {**ACETATE_K, "extraction_method": None}).phosphorus_potassium
    assert note.code == "PK_FROM_LAB_TEST"
    assert note.text.startswith(NITROGEN_ONLY_NOTE)
    assert "Potassium (K) was not checked against a pack table:" in note.text
    assert "No potassium" not in note.text and "No phosphorus" not in note.text


def test_note_without_any_table_result_is_nitrogen_only_too(pack: Pack) -> None:
    note = _run(
        pack,
        {**OLSEN_P, "extraction_method": None},
        {**ACETATE_K, "extraction_method": None},
    ).phosphorus_potassium
    assert note.code == "PK_NOT_CALCULATED_LAB_TEST"
    assert note.text.startswith("This plan covers nitrogen only: it has no P or K rate.")
    assert "the agronomist decides P and K from the soil test" in note.text


def test_a_pack_without_pk_config_keeps_the_old_note(
    lab_soil_test, make_input, placeholder_pack
) -> None:
    rec = recommend(make_input(soil_test=lab_soil_test()), placeholder_pack)
    assert rec.phosphorus_potassium.code == "PK_NOT_CALCULATED_V0"
    assert rec.phosphorus_potassium_rates is None
    assert "phosphorus_potassium_rates" not in rec.model_dump(mode="json")


def test_result_survives_a_json_round_trip(pack: Pack) -> None:
    rec = _run(pack, OLSEN_P, {**ACETATE_K, "extraction_method": None})
    dumped = json.loads(json.dumps(rec.model_dump(mode="json")))
    assert Recommendation.model_validate(dumped) == rec


def test_snapshot_keeps_the_missing_method(pack: Pack) -> None:
    rec = _run(pack, {**OLSEN_P, "extraction_method": None})
    assert rec.input_snapshot["soil_test"]["values"][0]["extraction_method"] is None
    assert SoilTest.model_validate(rec.input_snapshot["soil_test"]).values[0].value == 7


def _closed_table_pack(pack: Pack) -> Pack:
    data = copy.deepcopy(pack.model_dump(mode="json"))
    table = data["crops"]["wheat"]["phosphorus_potassium"]["nutrients"]["P"]["tables"]["olsen"]
    table["bands"] = [{"low": 5, "high": 9, "rate": 10, "response": "HR"}]
    return parse_pack(data)


@pytest.mark.parametrize("value", [4, 10])
def test_value_outside_a_closed_table_is_refused(pack: Pack, value: float) -> None:
    rates = _run(_closed_table_pack(pack), {**OLSEN_P, "value": value}).phosphorus_potassium_rates
    assert rates is not None
    line = _refused(rates.phosphorus)
    assert line.code == "outside_table"
    assert "5-9 ppm" in line.explanation


def test_nutrient_without_pack_guidance_is_refused(pack: Pack) -> None:
    data = copy.deepcopy(pack.model_dump(mode="json"))
    del data["crops"]["wheat"]["phosphorus_potassium"]["nutrients"]["K"]
    rates = _run(parse_pack(data), OLSEN_P, ACETATE_K).phosphorus_potassium_rates
    assert rates is not None
    assert _refused(rates.potassium).code == "no_pack_guidance"
    _recommended(rates.phosphorus)


@pytest.mark.parametrize(
    "name",
    [
        "sample_ca_on_pk_olsen_ammonium_acetate",
        "sample_ca_on_pk_oxide_form_input",
        "sample_ca_on_pk_missing_method",
        "sample_ca_on_pk_wrong_method_table",
        "sample_ca_on_pk_no_soil_test",
    ],
)
def test_golden_case_matches(pack: Pack, name: str) -> None:
    case = load_golden_case(GOLDEN_DIR / f"{name}.yaml")
    assert isinstance(case, ExpectedCase)
    rows = compare(case, recommend(case.input, pack))
    assert any(r.field.startswith("phosphorus_") for r in rows)
    assert [r.field for r in rows if not r.ok] == []


def test_golden_compare_reports_a_wrong_pk_rate(pack: Pack) -> None:
    path = GOLDEN_DIR / "sample_ca_on_pk_olsen_ammonium_acetate.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["expected"]["phosphorus"]["rate_oxide_kg_ha"] = 51.0
    case = parse_golden_case(data)
    assert isinstance(case, ExpectedCase)
    bad = [r.field for r in compare(case, recommend(case.input, pack)) if not r.ok]
    assert bad == ["phosphorus_rate_oxide_kg_ha"]


def test_golden_needs_pk_tolerances_for_pk_numbers() -> None:
    path = GOLDEN_DIR / "sample_ca_on_pk_olsen_ammonium_acetate.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["tolerance"]["kg_pk_per_ha"]
    with pytest.raises(ValueError, match="kg_pk_per_ha"):
        parse_golden_case(data)
