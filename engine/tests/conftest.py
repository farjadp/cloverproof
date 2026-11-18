"""Shared fixtures for engine tests."""

import copy
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from cloverproof_engine.loaders import load_pack
from cloverproof_engine.models import (
    ConcentrationUnit,
    ExtractionMethod,
    NutrientForm,
    RecommendationInput,
    SoilTest,
    SoilTestSource,
    SoilTestValue,
)
from cloverproof_engine.pack import Pack, parse_pack

REPO_ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER_PACK_PATH = REPO_ROOT / "packs" / "placeholder" / "v0.yaml"


@pytest.fixture
def placeholder_pack() -> Pack:
    return load_pack(PLACEHOLDER_PACK_PATH)


def _mark_validated(node: Any) -> None:
    if isinstance(node, dict):
        if "value" in node and "status" in node:
            node["status"] = "VALIDATED"
            node["source"] = "TEST FIXTURE ONLY - not a real source"
        for child in node.values():
            _mark_validated(child)
    elif isinstance(node, list):
        for child in node:
            _mark_validated(child)


def _validated_data() -> dict[str, Any]:
    data = copy.deepcopy(yaml.safe_load(PLACEHOLDER_PACK_PATH.read_text(encoding="utf-8")))
    _mark_validated(data)
    data["id"] = "test-validated"
    data["status"] = "validated"
    return data


@pytest.fixture
def validated_pack() -> Pack:
    """Same numbers as the placeholder pack, relabelled VALIDATED.

    Test-only: lets the confidence rules be exercised without the
    "pack has placeholders" cap. Never written to disk.
    """
    return parse_pack(_validated_data())


def _pack_with_placeholders(*paths: str) -> Pack:
    """Validated test pack with only the constants at `paths` set back to PLACEHOLDER.

    Paths use the engine's constant-path notation, e.g.
    "crops.wheat.nitrogen.soil_n_supply" or "crops.wheat.nitrogen.splits[0].fraction".
    """
    data = _validated_data()
    for path in paths:
        node: Any = data
        for part in path.replace("[", ".").replace("]", "").split("."):
            node = node[int(part)] if isinstance(node, list) else node[part]
        node["status"] = "PLACEHOLDER"
        node["source"] = None
    if paths:
        data["id"] = "test-mixed"
        data["status"] = "placeholder"
    return parse_pack(data)


@pytest.fixture
def pack_with_placeholders() -> Callable[..., Pack]:
    return _pack_with_placeholders


def _soil_value(
    form: NutrientForm,
    value: float,
    method: ExtractionMethod = ExtractionMethod.OLSEN,
    **extra: Any,
) -> SoilTestValue:
    """A soil-test value in mg/kg with its own extraction method."""
    return SoilTestValue.model_validate(
        {
            "form": form,
            "value": value,
            "unit": ConcentrationUnit.MG_PER_KG,
            "extraction_method": method,
            **extra,
        }
    )


def _lab_soil_test(**overrides: Any) -> SoilTest:
    data: dict[str, Any] = {
        "sample_date": date(2026, 9, 15),
        "depth_top_cm": 0.0,
        "depth_bottom_cm": 15.0,
        "source": SoilTestSource.LAB,
        "lab": "Example Lab",
        "values": [
            _soil_value(NutrientForm.P, 12.0),
            _soil_value(
                NutrientForm.K,
                150.0,
                ExtractionMethod.OTHER,
                extraction_method_detail="ammonium acetate",
            ),
        ],
    }
    data.update(overrides)
    return SoilTest.model_validate(data)


@pytest.fixture
def soil_value() -> Callable[..., SoilTestValue]:
    """Builder for one soil-test value in mg/kg (default extraction method Olsen)."""
    return _soil_value


@pytest.fixture
def lab_soil_test() -> Callable[..., SoilTest]:
    """Builder for a recent lab soil test, 0-15 cm: P (Olsen), K (other: ammonium acetate)."""
    return _lab_soil_test


def _soil_estimate_data(**overrides: Any) -> dict[str, Any]:
    """SYNTHETIC estimate in the input shape. Values are invented, not read from SoilGrids."""
    common = {"resolution_m": 250.0, "retrieved_on": "2026-11-18"}
    data: dict[str, Any] = {
        "provider": "SoilGrids",
        "version": "2.0",
        "attribution": "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0",
        "citation": "Poggio et al. 2021, SOIL 7, 217-240, doi:10.5194/soil-7-217-2021",
        "values": [
            {
                "property": "phh2o",
                "depth": "0-5cm",
                "value": 6.5,
                "unit": "pH",
                "q05": 5.8,
                "q95": 7.2,
                "uncertainty_ratio": 0.2,
                **common,
            },
            {"property": "nitrogen", "depth": "0-5cm", "value": 1500.0, "unit": "mg/kg", **common},
        ],
    }
    data.update(overrides)
    return data


@pytest.fixture
def soil_estimate_data() -> Callable[..., dict[str, Any]]:
    """Builder for a synthetic `soil_estimate` input mapping."""
    return _soil_estimate_data


@pytest.fixture
def make_input() -> Callable[..., RecommendationInput]:
    def build(**overrides: Any) -> RecommendationInput:
        data: dict[str, Any] = {
            "crop": "wheat",
            "target_yield_t_ha": 6.0,
            "previous_crop": "canola",
            "area_ha": 40.0,
            "plan_date": date(2027, 2, 15),
            "soil_test": None,
        }
        data.update(overrides)
        return RecommendationInput.model_validate(data)

    return build
