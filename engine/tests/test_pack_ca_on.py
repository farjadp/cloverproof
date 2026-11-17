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
from cloverproof_engine.methods.n_yield_price_table import PackValueNotSetError
from cloverproof_engine.models import (
    ConcentrationUnit,
    Crop,
    ExtractionMethod,
    NutrientForm,
    RecommendationInput,
    SoilTest,
)
from cloverproof_engine.pack import (
    ConstantStatus,
    Pack,
    UnsetConstant,
    YieldPriceTableNitrogen,
    pack_sha256,
)

CA_ON_PATH = Path(__file__).resolve().parents[2] / "packs" / "ca-on" / "v1.yaml"

# Fingerprint of packs/ca-on/v1.yaml. Change only on purpose (a pack edit needs a
# new pack version once any recommendation has recorded this one).
CA_ON_V1_SHA256 = "5be0fa3e0f0461549703dff0719a8d7791e426e65a71496b9abbe643ef2f5976"


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
        "n_price_ratio": 5.0,
    }
    data.update(change)
    return RecommendationInput.model_validate(data)


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
