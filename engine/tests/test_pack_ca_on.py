"""Pack ca-on v1 (Ontario winter wheat): loads, stays PLACEHOLDER, rules 2/3/7/9 hold.

These tests check structure and labelling, not agronomy. They do not repeat the
pack's numbers (those are checked by hand against the cited source and by the
golden report).
"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from cloverproof_engine import recommend
from cloverproof_engine.confidence import Confidence
from cloverproof_engine.loaders import load_pack
from cloverproof_engine.methods.n_yield_price_table import (
    MissingInputError,
    OutOfScopeError,
    PackValueNotSetError,
)
from cloverproof_engine.models import (
    ConcentrationUnit,
    Crop,
    ExtractionMethod,
    NutrientForm,
    RecommendationInput,
    SoilTest,
)
from cloverproof_engine.pack import (
    CitationBasis,
    ConstantStatus,
    Pack,
    PackConstant,
    UnsetConstant,
    YieldPriceTableNitrogen,
    pack_sha256,
)

CA_ON_PATH = Path(__file__).resolve().parents[2] / "packs" / "ca-on" / "v1.yaml"

# Fingerprint of packs/ca-on/v1.yaml. Change only on purpose (a pack edit needs a
# new pack version once any recommendation has recorded this one).
CA_ON_V1_SHA256 = "84d874e7c6f0119cfeb44e5c5de8a9dfe04e3e9961a0dae0819cd856b1996e58"


@pytest.fixture
def pack() -> Pack:
    return load_pack(CA_ON_PATH)


@pytest.fixture
def text() -> str:
    return CA_ON_PATH.read_text(encoding="utf-8")


def _input(**change: Any) -> RecommendationInput:
    data: dict[str, Any] = {
        "crop": "wheat",
        "target_yield_t_ha": 6.0,
        "previous_crop": "corn",
        "area_ha": 10.0,
        "plan_date": date(2027, 3, 1),
        # TEST FIXTURE ONLY: not real prices (ratio 1.25 / 0.25 = 5).
        "n_price": {
            "n_price_per_kg_n": 1.25,
            "grain_price_per_kg": 0.25,
            "currency": "CAD",
            "source": "TEST FIXTURE",
            "price_date": "2027-01-20",
        },
        "wheat_class": "pastry",
        "manure_applied": False,
    }
    data.update(change)
    for key in [k for k, v in data.items() if v is _DROP]:
        del data[key]
    return RecommendationInput.model_validate(data)


_DROP = object()  # marks an input key to leave out


def _lab_test() -> SoilTest:
    return SoilTest.model_validate(
        {
            "sample_date": "2026-09-15",
            "depth_top_cm": 0,
            "depth_bottom_cm": 15,
            "source": "lab",
            "lab": "TEST FIXTURE lab",
            "values": [
                {"form": "P", "value": 12.0, "unit": "mg/kg", "extraction_method": "olsen"},
                {
                    "form": "K",
                    "value": 120.0,
                    "unit": "mg/kg",
                    "extraction_method": "ammonium-acetate",
                },
            ],
        }
    )


def test_pack_loads_with_identity(pack: Pack) -> None:
    assert (pack.id, pack.version, pack.status) == ("ca-on", "v1", "placeholder")
    assert Crop.WHEAT in pack.crops
    assert isinstance(pack.crops[Crop.WHEAT].nitrogen, YieldPriceTableNitrogen)


def test_every_constant_is_placeholder_without_source(pack: Pack) -> None:
    constants = list(pack.iter_constants())
    assert constants
    assert pack.has_placeholders
    for c in constants:
        assert c.status is ConstantStatus.PLACEHOLDER
        assert c.source is None


def test_every_placeholder_has_a_todo_agronomist(text: str) -> None:
    # One TODO(agronomist) per labelled block (a table carries one label).
    assert text.count("TODO(agronomist)") >= text.count("status: PLACEHOLDER")


def test_unset_values_are_declared_not_guessed(pack: Pack) -> None:
    unset = [c for c in pack.iter_constants() if isinstance(c, UnsetConstant)]
    assert pack.unset_constants == len(unset) > 0


def test_cited_constants_carry_full_citation(pack: Pack) -> None:
    cited = [c for c in pack.iter_constants() if c.citation is not None]
    assert cited
    for c in cited:
        assert c.citation.url.startswith("https://")
        assert c.citation.accessed_on <= date(2026, 11, 17)


def test_soil_test_methods_are_explicit(pack: Pack) -> None:
    methods = pack.crops[Crop.WHEAT].soil_test_methods
    assert methods is not None
    p, k = methods["P"], methods["K"]
    assert (p.form, p.unit, p.extraction_method) == (
        NutrientForm.P,
        ConcentrationUnit.MG_PER_KG,
        ExtractionMethod.OLSEN,
    )
    assert (k.form, k.unit, k.extraction_method) == (
        NutrientForm.K,
        ConcentrationUnit.MG_PER_KG,
        ExtractionMethod.AMMONIUM_ACETATE,
    )
    assert p.citation is not None and k.citation is not None


def test_sha256_is_stable(pack: Pack) -> None:
    assert pack_sha256(pack) == pack_sha256(load_pack(CA_ON_PATH))
    assert pack_sha256(pack) == CA_ON_V1_SHA256


def test_sha256_ignores_comments(tmp_path: Path, text: str) -> None:
    raw = yaml.safe_load(text)
    copy_path = tmp_path / "v1.yaml"
    copy_path.write_text(yaml.safe_dump(raw, sort_keys=True), encoding="utf-8")
    assert pack_sha256(load_pack(copy_path)) == pack_sha256(load_pack(CA_ON_PATH))


def test_no_soil_test_is_n_only_and_at_most_medium(pack: Pack) -> None:
    rec = recommend(_input(), pack)
    assert rec.nitrogen.nutrient == "N"
    assert rec.phosphorus_potassium.code == "PK_SOIL_TEST_RECOMMENDED"
    assert rec.confidence <= Confidence.MEDIUM


def test_placeholder_pack_caps_confidence_low(pack: Pack) -> None:
    rec = recommend(_input(soil_test=_lab_test()), pack)
    assert rec.confidence is Confidence.LOW
    assert any(n.code == "PACK_HAS_PLACEHOLDERS" for n in rec.notes)


def test_lab_soil_test_still_gives_no_pk_rate(pack: Pack) -> None:
    rec = recommend(_input(soil_test=_lab_test()), pack)
    assert rec.phosphorus_potassium.code == "PK_NOT_CALCULATED_V0"


def test_rate_comes_from_the_table_with_explanation(pack: Pack) -> None:
    rec = recommend(_input(), pack)
    assert rec.nitrogen.method_id == "n_yield_price_table"
    assert rec.nitrogen.rate.uses_placeholder
    assert rec.nitrogen.rate.explanation
    assert rec.pack_sha256 == pack_sha256(pack)


def test_previous_crop_without_a_credit_refuses(pack: Pack) -> None:
    credits = pack.crops[Crop.WHEAT].nitrogen.previous_crop_credits
    unset = [key for key, crop in credits.items() if isinstance(crop.credit, UnsetConstant)]
    assert unset
    with pytest.raises(PackValueNotSetError):
        recommend(_input(previous_crop=unset[0]), pack)


# --- review fixes: citation basis and source corrections (PR #41) ---------------------


def _basis(c: PackConstant | UnsetConstant) -> CitationBasis:
    assert c.citation is not None
    return c.citation.basis


def test_citation_basis_per_constant(pack: Pack) -> None:
    n = pack.crops[Crop.WHEAT].nitrogen
    assert isinstance(n, YieldPriceTableNitrogen)
    assert all(_basis(cell) is CitationBasis.STATED for cell in n.rate_table.cells())
    assert _basis(n.max_rate) is CitationBasis.DERIVED
    assert _basis(n.splits[0].fraction) is CitationBasis.DERIVED
    credits = n.previous_crop_credits
    assert _basis(credits["corn"].credit) is CitationBasis.INFERRED
    assert _basis(credits["wheat"].credit) is CitationBasis.INFERRED
    assert _basis(credits["soybean"].credit) is CitationBasis.STATED
    conf = pack.crops[Crop.WHEAT].confidence
    assert _basis(conf.target_yield_min) is CitationBasis.DERIVED
    assert _basis(conf.target_yield_max) is CitationBasis.DERIVED


def test_table_4_14_is_cited_by_its_title(pack: Pack) -> None:
    n = pack.crops[Crop.WHEAT].nitrogen
    assert isinstance(n, YieldPriceTableNitrogen)
    assert n.rate_table.citation is not None
    assert "Table 4-14, Nitrogen requirements for pastry wheat" in n.rate_table.citation.locator


def test_corn_credit_explanation_says_inferred_not_read_from(pack: Pack) -> None:
    rec = recommend(_input(previous_crop="corn"), pack)
    credit = next(c for c in rec.nitrogen.components if c.name == "previous_crop_credit")
    assert "inferred" in credit.explanation
    assert "read from" not in credit.explanation


def test_soybean_credit_is_zero_as_stated_in_table_9_9(pack: Pack) -> None:
    soybean = pack.crops[Crop.WHEAT].nitrogen.previous_crop_credits["soybean"].credit
    assert isinstance(soybean, PackConstant) and soybean.value == 0
    assert soybean.citation is not None and "Table 9-9" in soybean.citation.locator
    rec = recommend(_input(previous_crop="soybean"), pack)
    credit = next(c for c in rec.nitrogen.components if c.name == "previous_crop_credit")
    assert "read from" in credit.explanation and "Table 9-9" in credit.explanation


def test_legume_sod_refuses_and_names_the_missing_input(pack: Pack) -> None:
    legume = pack.crops[Crop.WHEAT].nitrogen.previous_crop_credits["legume_sod"].credit
    assert isinstance(legume, UnsetConstant)
    assert legume.citation is not None and "Table 9-9" in legume.citation.locator
    with pytest.raises(PackValueNotSetError, match="legume fraction"):
        recommend(_input(previous_crop="legume_sod"), pack)


def test_spring_timing_is_the_table_4_14_header_not_a_growth_stage(pack: Pack, text: str) -> None:
    assert "GS25" not in text and "GS30" not in text
    split = pack.crops[Crop.WHEAT].nitrogen.splits[0]
    assert "early spring" in split.stage_label.lower()
    assert "10 kg N/ha at seeding" in split.stage_label
    assert split.timing_citation is not None
    assert split.timing_citation.basis is CitationBasis.STATED
    assert "Table 4-14" in split.timing_citation.locator
    rec = recommend(_input(), pack)
    assert "read from" in rec.nitrogen.splits[0].fraction.explanation


# --- S1 wheat class (pastry only) and S2 manure ------------------------------------


def test_wheat_class_is_required(pack: Pack) -> None:
    with pytest.raises(MissingInputError, match="wheat_class"):
        recommend(_input(wheat_class=_DROP), pack)


def test_hard_wheat_is_refused(pack: Pack) -> None:
    with pytest.raises(OutOfScopeError, match="hard wheat is not covered"):
        recommend(_input(wheat_class="hard"), pack)


def test_rate_explanation_states_pastry_scope(pack: Pack) -> None:
    rec = recommend(_input(), pack)
    assert "pastry (soft) wheat only, Table 4-14" in rec.nitrogen.rate.explanation
    assert rec.input_snapshot["wheat_class"] == "pastry"


def test_manure_applied_is_required(pack: Pack) -> None:
    with pytest.raises(MissingInputError, match="manure_applied"):
        recommend(_input(manure_applied=_DROP), pack)


def test_manure_applied_is_refused(pack: Pack) -> None:
    with pytest.raises(OutOfScopeError, match="manure"):
        recommend(_input(manure_applied=True), pack)


def test_no_manure_is_stated_in_the_rate_explanation(pack: Pack) -> None:
    rec = recommend(_input(), pack)
    assert "assumes no manure applied" in rec.nitrogen.rate.explanation.lower()
    assert rec.input_snapshot["manure_applied"] is False
