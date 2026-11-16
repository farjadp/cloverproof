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


@pytest.fixture
def validated_pack() -> Pack:
    """Same numbers as the placeholder pack, relabelled VALIDATED.

    Test-only: lets the confidence rules be exercised without the
    "pack has placeholders" cap. Never written to disk.
    """
    data = copy.deepcopy(yaml.safe_load(PLACEHOLDER_PACK_PATH.read_text(encoding="utf-8")))
    _mark_validated(data)
    data["id"] = "test-validated"
    data["status"] = "validated"
    return parse_pack(data)


def _lab_soil_test(**overrides: Any) -> SoilTest:
    data: dict[str, Any] = {
        "sample_date": date(2026, 9, 15),
        "depth_top_cm": 0.0,
        "depth_bottom_cm": 15.0,
        "extraction_method": ExtractionMethod.OLSEN,
        "source": SoilTestSource.LAB,
        "lab": "Example Lab",
        "values": [
            SoilTestValue(form=NutrientForm.P, value=12.0, unit=ConcentrationUnit.MG_PER_KG),
            SoilTestValue(form=NutrientForm.K, value=150.0, unit=ConcentrationUnit.MG_PER_KG),
        ],
    }
    data.update(overrides)
    return SoilTest.model_validate(data)


@pytest.fixture
def lab_soil_test() -> Callable[..., SoilTest]:
    """Builder for a recent lab soil test (P and K in mg/kg, Olsen, 0-15 cm)."""
    return _lab_soil_test


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
