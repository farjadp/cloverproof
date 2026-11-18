"""Product matching (S2-ENG-05): N need -> catalog product -> quantity.

Every product, grade, density and rule here is a TEST FIXTURE, not agronomy.
"""

import copy
import json
import math
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from cloverproof_engine import recommend
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.golden import ExpectedCase, compare
from cloverproof_engine.loaders import load_golden_case, load_pack, pack_path, read_yaml
from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import Pack, pack_sha256, parse_pack
from cloverproof_engine.results import (
    ProductMatch,
    ProductNotMatched,
    Recommendation,
    SplitApplication,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKS_DIR = REPO_ROOT / "packs"
GOLDEN_DIR = REPO_ROOT / "engine" / "tests" / "golden"
RULES_PATH = PACKS_DIR / "placeholder" / "v0-product-rules.yaml"
V0_PATH = PACKS_DIR / "placeholder" / "v0.yaml"
CA_ON_PATH = PACKS_DIR / "ca-on" / "v1.yaml"

# Fingerprint before product matching (engine 0.4.0): this pack must not change.
CA_ON_V1_SHA256 = "84d874e7c6f0119cfeb44e5c5de8a9dfe04e3e9961a0dae0819cd856b1996e58"

LIQUID = "TEST FIXTURE liquid N 25"
GRANULAR = "TEST FIXTURE granular N 40"
C7 = "C7_PLACEHOLDER_PRODUCT_RULE_USED"


def product(name: str = GRANULAR, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": f"id-{name}",
        "name": name,
        "n_pct": 40,
        "p2o5_pct": 0,
        "k2o_pct": 0,
        "s_pct": 0,
        "form": "granular",
        "grade_source": "test fixture",
    }
    data.update(overrides)
    return data


def liquid(name: str = LIQUID, **overrides: Any) -> dict[str, Any]:
    return product(name, **{"n_pct": 25, "form": "liquid", "density_kg_per_l": 1.25, **overrides})


def inputs(products: list[dict[str, Any]] | None, **overrides: Any) -> RecommendationInput:
    data: dict[str, Any] = {
        "crop": "wheat",
        "target_yield_t_ha": 5.3,
        "previous_crop": "canola",
        "area_ha": 40.0,
        "plan_date": "2027-02-15",
    }
    if products is not None:
        data["products"] = products
    data.update(overrides)
    return RecommendationInput.model_validate(data)


def raw_rules_pack() -> dict[str, Any]:
    return copy.deepcopy(read_yaml(RULES_PATH))


def rules_pack(**rule_values: Any) -> Pack:
    """TEST FIXTURE pack with some rule values replaced."""
    data = raw_rules_pack()
    rules = data["crops"]["wheat"]["product_rules"]
    for name, value in rule_values.items():
        rules[name]["value"] = value
    return parse_pack(data)


@pytest.fixture
def no_rule_pack() -> Pack:
    return load_pack(V0_PATH)


def lines(rec: Recommendation) -> list[SplitApplication]:
    return rec.nitrogen.splits


def matched(rec: Recommendation, index: int = 0) -> ProductMatch:
    result = lines(rec)[index].product_match
    assert isinstance(result, ProductMatch)
    return result


def unmatched(rec: Recommendation, index: int = 0) -> ProductNotMatched:
    result = lines(rec)[index].product_match
    assert isinstance(result, ProductNotMatched)
    return result


# --- golden -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id", ["sample_wheat_product_match_liquid", "sample_wheat_product_none_fits"]
)
def test_product_golden_cases_agree(case_id: str) -> None:
    case = load_golden_case(GOLDEN_DIR / f"{case_id}.yaml")
    assert isinstance(case, ExpectedCase)
    pack = load_pack(pack_path(PACKS_DIR, case.pack.id, case.pack.version))
    rows = compare(case, recommend(case.input, pack))
    assert [r.field for r in rows if not r.ok] == []
    assert any("product" in r.field for r in rows)


def test_golden_compare_flags_a_wrong_product() -> None:
    case = load_golden_case(GOLDEN_DIR / "sample_wheat_product_none_fits.yaml")
    assert isinstance(case, ExpectedCase)
    rec = recommend(inputs([product()]), rules_pack(allow_single_fit=True))
    rows = {r.field: r for r in compare(case, rec)}
    assert not rows["split_1_product"].ok
    assert not rows["split_1_product_kg_ha"].ok


def test_golden_product_expectation_needs_product_tolerances() -> None:
    data = read_yaml(GOLDEN_DIR / "sample_wheat_product_match_liquid.yaml")
    del data["tolerance"]["kg_product_per_ha"]
    with pytest.raises(ValidationError, match="kg_product_per_ha"):
        ExpectedCase.model_validate(data)


# --- quantities -------------------------------------------------------------------


def test_granular_quantity_is_need_over_grade() -> None:
    rec = recommend(inputs([product()]), rules_pack())
    first, second = matched(rec, 0), matched(rec, 1)
    assert first.rate.value == pytest.approx(59.5 / 0.4)
    assert first.rate.unit == "kg product/ha"
    assert first.total.value == pytest.approx(59.5 / 0.4 * 40)
    assert first.total.unit == "kg product"
    assert second.rate.value == pytest.approx(89.25 / 0.4)
    assert first.volume_rate is None


def test_liquid_gets_litres_through_density() -> None:
    match = matched(recommend(inputs([liquid()]), rules_pack()))
    assert match.rate.value == pytest.approx(238.0)
    assert match.volume_rate is not None
    assert match.volume_rate.value == pytest.approx(190.4)
    assert match.volume_rate.unit == "L product/ha"
    assert "1.25 kg/L" in match.volume_rate.explanation


def test_match_identifies_product_grade_and_forms() -> None:
    match = matched(recommend(inputs([liquid()]), rules_pack()))
    assert (match.product_id, match.product_name) == (f"id-{LIQUID}", LIQUID)
    assert match.form == "liquid"
    assert match.grade_source == "test fixture"
    assert match.grade.n.value == 25
    assert match.grade.n.unit == "% N"
    assert match.grade.p2o5.unit == "% P2O5"
    assert match.grade.k2o.unit == "% K2O"
    assert match.grade.s.unit == "% S"


def test_every_match_number_is_explained_and_labelled() -> None:
    match = matched(recommend(inputs([liquid(s_pct=5)]), rules_pack(sulphur="allow")))
    assert match.sulphur_rate is not None and match.volume_rate is not None
    for number in (match.rate, match.total, match.volume_rate, match.sulphur_rate):
        assert number.explanation.strip()
        assert number.uses_placeholder is True
    for number in (match.grade.n, match.grade.p2o5, match.grade.k2o, match.grade.s):
        assert "test fixture" in number.explanation
    assert "PLACEHOLDER" in match.explanation
    assert match.rules_used
    assert all(r.status == "PLACEHOLDER" for r in match.rules_used)


# --- hard safety ------------------------------------------------------------------


@pytest.mark.parametrize("grade", [{"p2o5_pct": 1}, {"k2o_pct": 1}, {"p2o5_pct": 5, "k2o_pct": 5}])
@pytest.mark.parametrize("soil", [False, True])
def test_a_product_with_p_or_k_never_matches(grade: dict[str, float], soil: bool) -> None:
    soil_test = {
        "sample_date": "2026-09-01",
        "depth_top_cm": 0,
        "depth_bottom_cm": 15,
        "source": "lab",
        "values": [{"form": "P", "value": 10, "unit": "mg/kg", "extraction_method": "olsen"}],
    }
    # Even when it is the pack's first preference and single fits are allowed.
    pack = rules_pack(preference=[GRANULAR], allow_single_fit=True)
    rec = recommend(inputs([product(**grade)], soil_test=soil_test if soil else None), pack)
    result = unmatched(rec)
    assert result.code == "none_fit"
    assert GRANULAR in result.explanation
    assert "P or K" in result.explanation


def test_a_product_without_n_never_matches() -> None:
    pack = rules_pack(preference=[GRANULAR], allow_single_fit=True)
    result = unmatched(recommend(inputs([product(n_pct=0, s_pct=20)]), pack))
    assert result.code == "none_fit"
    assert "no N" in result.explanation


# --- sulphur ----------------------------------------------------------------------


def test_sulphur_product_is_excluded_when_the_pack_says_so() -> None:
    pack = rules_pack(preference=[GRANULAR], allow_single_fit=True, sulphur="exclude")
    result = unmatched(recommend(inputs([product(s_pct=10)]), pack))
    assert result.code == "none_fit"
    assert "sulphur" in result.explanation
    assert "PLACEHOLDER" in result.explanation


def test_allowed_sulphur_is_quantified_and_stated() -> None:
    match = matched(recommend(inputs([product(n_pct=20, s_pct=10)]), rules_pack(sulphur="allow")))
    assert match.sulphur_rate is not None
    assert match.sulphur_rate.value == pytest.approx(59.5 / 0.2 * 0.1)
    assert match.sulphur_rate.unit == "kg S/ha"
    assert "no sulphur recommendation" in match.explanation


def test_a_sulphur_free_match_says_so() -> None:
    match = matched(recommend(inputs([product()]), rules_pack()))
    assert match.sulphur_rate is None
    assert "contains no sulphur" in match.explanation


# --- choice rule ------------------------------------------------------------------


def test_preference_order_wins_whatever_the_input_order() -> None:
    pack = rules_pack()
    for products in ([product(), liquid()], [liquid(), product()]):
        match = matched(recommend(inputs(products), pack))
        assert match.product_name == LIQUID
        assert match.selection == "pack_preference"


def test_preference_skips_a_product_that_does_not_fit() -> None:
    pack = rules_pack(allowed_forms=["granular"])
    assert matched(recommend(inputs([product(), liquid()]), pack)).product_name == GRANULAR


def test_preference_names_match_without_case() -> None:
    pack = rules_pack(preference=[GRANULAR.lower()])
    assert matched(recommend(inputs([product()]), pack)).product_name == GRANULAR


def test_several_fit_without_preference_lists_them_and_picks_none() -> None:
    other = "TEST FIXTURE granular N 30"
    rec = recommend(inputs([product(other, n_pct=30), product()]), rules_pack(preference=[]))
    result = unmatched(rec)
    assert result.code == "several_fit"
    assert result.fitting_products == sorted([other, GRANULAR])
    assert other in result.explanation and GRANULAR in result.explanation


def test_single_fit_needs_the_pack_permission() -> None:
    products = [product("TEST FIXTURE other", n_pct=30)]
    refused = unmatched(recommend(inputs(products), rules_pack(preference=[])))
    assert refused.code == "single_fit_not_allowed"
    assert refused.fitting_products == ["TEST FIXTURE other"]
    allowed = matched(recommend(inputs(products), rules_pack(preference=[], allow_single_fit=True)))
    assert allowed.selection == "single_fit"


@pytest.mark.parametrize("count", [1, 2])
def test_pack_without_rules_never_selects(no_rule_pack: Pack, count: int) -> None:
    products = [product(), liquid()][:count]
    result = unmatched(recommend(inputs(products), no_rule_pack))
    assert result.code == "no_choice_rule"
    assert result.fitting_products == sorted(p["name"] for p in products)
    assert result.rules_used == []


def test_pack_without_rules_flags_sulphur_in_the_fitting_list(no_rule_pack: Pack) -> None:
    result = unmatched(recommend(inputs([product(s_pct=10)]), no_rule_pack))
    assert "sulphur" in result.explanation


def test_pack_without_rules_and_no_safe_product(no_rule_pack: Pack) -> None:
    result = unmatched(recommend(inputs([product(k2o_pct=5)]), no_rule_pack))
    assert result.code == "none_fit"
    assert result.fitting_products == []


def test_empty_catalog_says_so() -> None:
    rec = recommend(inputs([]), rules_pack())
    assert unmatched(rec).code == "no_products"
    assert unmatched(rec).explanation.strip()


def test_line_with_no_n_needs_no_product() -> None:
    # Fixture inputs that drive the N rate to the pack minimum of 0.
    rec = recommend(
        inputs([product()], target_yield_t_ha=1.0, previous_crop="soybean"), rules_pack()
    )
    assert rec.nitrogen.rate.value == 0
    assert unmatched(rec).code == "no_n_needed"


# --- what must not change ----------------------------------------------------------


def test_matching_changes_no_nutrient_number_and_only_adds_c7() -> None:
    pack = rules_pack()
    without = recommend(inputs(None), pack)
    with_match = recommend(inputs([product()]), pack)
    assert with_match.nitrogen.rate == without.nitrogen.rate
    assert [s.rate for s in lines(with_match)] == [s.rate for s in lines(without)]
    assert with_match.confidence == without.confidence
    assert with_match.confidence_reasons[:-1] == without.confidence_reasons
    assert with_match.confidence_reasons[-1].rule_id == C7
    assert with_match.notes == without.notes


def test_a_line_without_a_match_leaves_confidence_alone() -> None:
    pack = rules_pack(preference=[])
    without = recommend(inputs(None), pack)
    other = product("TEST FIXTURE other", n_pct=30)
    rec = recommend(inputs([product(), other]), pack)
    assert unmatched(rec).code == "several_fit"
    assert unmatched(rec).rules_used
    assert rec.confidence_reasons == without.confidence_reasons


# --- confidence: unvalidated product rule --------------------------------------------


def validated_pack_with_placeholder_rules() -> Pack:
    """TEST FIXTURE: only the product rules are unvalidated, and no timing window applies."""
    raw = raw_rules_pack()
    data = _all_validated(raw_rules_pack())
    data["status"] = raw["status"]
    wheat = data["crops"]["wheat"]
    wheat["product_rules"] = raw["crops"]["wheat"]["product_rules"]
    del wheat["nitrogen"]["splits"]
    return parse_pack(data)


def test_a_placeholder_product_rule_caps_confidence_at_low() -> None:
    pack = validated_pack_with_placeholder_rules()
    assert recommend(inputs(None), pack).confidence == Confidence.MEDIUM
    rec = recommend(inputs([product()]), pack)
    assert rec.confidence == Confidence.LOW
    hit = next(h for h in rec.confidence_reasons if h.rule_id == C7)
    assert hit.cap == Confidence.LOW
    for rule in matched(rec).rules_used:
        assert hit.reason.count(rule.path) == 1


def test_validated_product_rules_do_not_fire_c7() -> None:
    rec = recommend(inputs([product()]), parse_pack(_all_validated(raw_rules_pack())))
    assert isinstance(lines(rec)[0].product_match, ProductMatch)
    assert C7 not in [h.rule_id for h in rec.confidence_reasons]


# --- quantities that cannot be computed ----------------------------------------------


@pytest.mark.parametrize(
    "catalog",
    [
        [product(n_pct=1e-320)],
        [product(n_pct=5e-324)],
        [liquid(density_kg_per_l=1e-320)],
    ],
)
def test_an_unusable_grade_or_density_is_a_coded_non_match(catalog: list[dict[str, Any]]) -> None:
    pack = rules_pack(preference=[catalog[0]["name"]])
    rec = recommend(inputs(catalog), pack)
    for i, line in enumerate(lines(rec), 1):
        result = line.product_match
        assert isinstance(result, ProductNotMatched)
        assert result.code == "quantity_out_of_range"
        assert result.fitting_products == []
        assert catalog[0]["name"] in result.explanation
        assert f"application {i}" in result.explanation
    assert Recommendation.model_validate(rec.model_dump(mode="json")) == rec


def test_a_field_total_too_large_to_compute_is_a_coded_non_match() -> None:
    rec = recommend(inputs([product()], area_ha=1e308), rules_pack())
    assert unmatched(rec).code == "quantity_out_of_range"


# --- rule citations ------------------------------------------------------------------


def cited_rules_pack(basis: str) -> Pack:
    citation: dict[str, Any] = {
        "title": "TEST FIXTURE guide",
        "publisher": "TEST FIXTURE publisher",
        "year": 2020,
        "locator": "Table 1",
        "url": "https://example.org/fixture",
        "accessed_on": "2026-11-01",
        "basis": basis,
    }
    if basis != "stated":
        citation["note"] = "TEST FIXTURE note"
    data = raw_rules_pack()
    data["crops"]["wheat"]["product_rules"]["sulphur"]["citation"] = citation
    return parse_pack(data)


@pytest.mark.parametrize(
    ("basis", "wording"),
    [
        ("stated", "read from TEST FIXTURE guide, Table 1"),
        ("derived", "derived by the engine from TEST FIXTURE guide, Table 1"),
        ("inferred", "inferred by the engine from TEST FIXTURE guide, Table 1"),
    ],
)
def test_a_cited_rule_is_copied_and_shown_by_basis(basis: str, wording: str) -> None:
    rec = recommend(inputs([product()]), cited_rules_pack(basis))
    match = matched(rec)
    rule = next(r for r in match.rules_used if r.path.endswith(".sulphur"))
    assert rule.citation is not None
    assert rule.citation.basis == basis
    rules_text = match.explanation.split("Rules used: ")[1]
    assert wording in rules_text
    assert ("read from" in rules_text) is (basis == "stated")
    assert Recommendation.model_validate(rec.model_dump(mode="json")) == rec


def test_a_rule_without_citation_has_none() -> None:
    match = matched(recommend(inputs([product()]), rules_pack()))
    assert all(r.citation is None for r in match.rules_used)


# --- explanation operands -------------------------------------------------------------


def test_product_explanations_can_be_reproduced_by_hand() -> None:
    catalog = [liquid(s_pct=5)]
    match = matched(recommend(inputs(catalog), rules_pack(sulphur="allow")), 1)
    assert match.volume_rate is not None and match.sulphur_rate is not None
    assert "89.25 kg N/ha / 25 % N = 357.0 kg product/ha" in match.rate.explanation
    assert "357 kg product/ha x 40 ha = 14,280.0 kg product" in match.total.explanation
    assert "357 kg product/ha / 1.25 kg/L" in match.volume_rate.explanation
    assert "357 kg product/ha x 5 % S = 17.9 kg S/ha" in match.sulphur_rate.explanation


def test_absent_products_leave_input_and_output_shape_alone() -> None:
    rec = recommend(inputs(None), rules_pack())
    assert "products" not in rec.input_snapshot
    for line in rec.model_dump(mode="json")["nitrogen"]["splits"]:
        assert "product_match" not in line


def test_products_land_in_the_input_snapshot() -> None:
    rec = recommend(inputs([liquid()]), rules_pack())
    assert rec.input_snapshot["products"][0]["name"] == LIQUID
    assert rec.input_snapshot["products"][0]["density_kg_per_l"] == 1.25


@pytest.mark.parametrize("products", [[product()], [product(k2o_pct=5)]])
def test_output_round_trips_through_json(products: list[dict[str, Any]]) -> None:
    rec = recommend(inputs(products), rules_pack())
    assert Recommendation.model_validate(rec.model_dump(mode="json")) == rec


def test_output_has_no_commercial_fields() -> None:
    rec = recommend(inputs([product(), liquid()]), rules_pack())
    text = json.dumps(rec.model_dump(mode="json")["nitrogen"]["splits"]).lower()
    for word in ("price", "vendor", "cost", "commission", "supplier"):
        assert word not in text


def test_shipped_packs_have_no_rules_and_keep_their_fingerprint() -> None:
    assert load_pack(V0_PATH).crops["wheat"].product_rules is None
    ca_on = load_pack(CA_ON_PATH)
    assert ca_on.crops["wheat"].product_rules is None
    assert pack_sha256(ca_on) == CA_ON_V1_SHA256


# --- input validation --------------------------------------------------------------


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (product(form="liquid"), "density"),
        (product(density_kg_per_l=1.2), "density"),
        (liquid(density_kg_per_l=0), "density"),
        (liquid(density_kg_per_l=math.inf), "density"),
        (product(n_pct=60, s_pct=50), "100"),
        (product(n_pct=-1), "n_pct"),
        (product(name="  "), "name"),
        (product(grade_source=" "), "grade_source"),
        (product(form="pellet"), "form"),
        (product(price=1), "price"),
    ],
)
def test_bad_product_input_is_rejected(bad: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        inputs([bad])


def test_sulphur_grade_must_be_given() -> None:
    bad = product()
    del bad["s_pct"]
    with pytest.raises(ValidationError, match="s_pct"):
        inputs([bad])


def test_duplicate_products_are_rejected() -> None:
    with pytest.raises(ValidationError, match="id"):
        inputs([product(), product("other", id=f"id-{GRANULAR}")])
    with pytest.raises(ValidationError, match="name"):
        inputs([product(), product(GRANULAR.lower(), id="other")])


# --- pack validation ---------------------------------------------------------------


def rule_change(name: str, **fields: Any) -> dict[str, Any]:
    data = raw_rules_pack()
    data["crops"]["wheat"]["product_rules"][name].update(fields)
    return data


@pytest.mark.parametrize(
    ("name", "fields"),
    [
        ("sulphur", {"value": "ignore"}),
        ("allowed_forms", {"value": []}),
        ("allowed_forms", {"value": ["granular", "granular"]}),
        ("allowed_forms", {"value": ["pellet"]}),
        ("allow_single_fit", {"value": "yes"}),
        ("preference", {"value": ["A", "a"]}),
        ("preference", {"value": [" "]}),
        ("sulphur", {"source": "a book"}),
        ("sulphur", {"status": "VALIDATED"}),
    ],
)
def test_bad_product_rules_are_rejected(name: str, fields: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse_pack(rule_change(name, **fields))


def test_every_product_rule_is_required() -> None:
    data = raw_rules_pack()
    del data["crops"]["wheat"]["product_rules"]["sulphur"]
    with pytest.raises(ValidationError, match="sulphur"):
        parse_pack(data)


def test_fixture_rules_are_all_placeholder() -> None:
    rules = list(load_pack(RULES_PATH).iter_product_rules())
    assert len(rules) == 4
    assert all(r.is_placeholder and r.source is None for r in rules)


def _all_validated(node: Any) -> Any:
    """TEST FIXTURE: mark every labelled value VALIDATED, to test the pack-level check."""
    if isinstance(node, dict):
        if node.get("status") == "PLACEHOLDER":
            node.update(status="VALIDATED", source="test fixture")
        elif node.get("status") == "placeholder":
            node["status"] = "validated"
        for child in node.values():
            _all_validated(child)
    elif isinstance(node, list):
        for child in node:
            _all_validated(child)
    return node


def test_validated_pack_refuses_a_placeholder_rule() -> None:
    placeholder_rule = raw_rules_pack()["crops"]["wheat"]["product_rules"]["sulphur"]
    data = _all_validated(raw_rules_pack())
    data["crops"]["wheat"]["product_rules"]["sulphur"] = placeholder_rule
    with pytest.raises(ValidationError, match="PLACEHOLDER"):
        parse_pack(data)


def test_fully_validated_rules_are_accepted() -> None:
    pack = parse_pack(_all_validated(raw_rules_pack()))
    assert not pack.has_placeholders
    match = matched(recommend(inputs([product()]), pack))
    assert match.rate.uses_placeholder is False
    assert "PLACEHOLDER" not in match.explanation
