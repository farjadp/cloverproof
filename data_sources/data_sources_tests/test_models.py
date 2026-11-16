"""N-only guard on the estimate schema (CLAUDE.md hard rule 3)."""

import re
import typing
from datetime import date

import pytest
from pydantic import ValidationError

from data_sources.soilgrids.models import EstimateValue, SoilEstimate

PK_PATTERN = re.compile(r"(^|_)(p|k|p2o5|k2o|phosph\w*|potass\w*|olsen|bray\w*|mehlich\w*)($|_)")


def _value(**over: object) -> EstimateValue:
    data: dict[str, object] = {
        "property": "nitrogen",
        "depth": "0-5cm",
        "depth_top_cm": 0,
        "depth_bottom_cm": 5,
        "statistic": "mean",
        "value": 1500.0,
        "unit": "mg/kg",
        "mapped_value": 150,
        "mapped_unit": "cg/kg",
        "conversion_factor_source": "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html",
        "q05": 800.0,
        "q95": 3000.0,
        "uncertainty_ratio": 1.5,
        "url": "https://files.isric.org/soilgrids/latest/data/nitrogen/nitrogen_0-5cm_mean.vrt",
        "retrieved_on": date(2026, 11, 16),
        "resolution_m": 250.0,
    }
    data.update(over)
    return EstimateValue.model_validate(data)


def _estimate(**over: object) -> SoilEstimate:
    data: dict[str, object] = {"lon": -80.25, "lat": 43.55, "values": (_value(),)}
    data.update(over)
    return SoilEstimate.model_validate(data)


def _all_field_names(model: type) -> set[str]:
    names = set(model.model_fields)
    for f in model.model_fields.values():
        for arg in typing.get_args(f.annotation) or (f.annotation,):
            if isinstance(arg, type) and hasattr(arg, "model_fields"):
                names |= _all_field_names(arg)
    return names


def test_schema_has_no_phosphorus_or_potassium_field() -> None:
    names = _all_field_names(SoilEstimate) | _all_field_names(EstimateValue)
    offenders = {n for n in names if PK_PATTERN.search(n.lower())}
    assert not offenders, offenders


def test_property_literal_has_no_p_or_k() -> None:
    allowed = set(typing.get_args(EstimateValue.model_fields["property"].annotation))
    assert allowed == {"phh2o", "soc", "nitrogen", "clay", "sand", "silt"}
    with pytest.raises(ValidationError):
        _value(property="phosphorus")


@pytest.mark.parametrize("extra", ["phosphorus", "potassium", "p_mg_kg", "k_mg_kg"])
def test_extra_fields_are_forbidden(extra: str) -> None:
    with pytest.raises(ValidationError):
        _estimate(**{extra: 12.0})
    with pytest.raises(ValidationError):
        _value(**{extra: 12.0})


def test_source_is_always_estimate() -> None:
    est = _estimate()
    assert est.source == "estimate"
    assert typing.get_args(SoilEstimate.model_fields["source"].annotation) == ("estimate",)
    with pytest.raises(ValidationError):
        _estimate(source="lab")


def test_confidence_is_fixed_low() -> None:
    est = _estimate()
    assert est.confidence == "low"
    with pytest.raises(ValidationError):
        _estimate(confidence="medium")
    with pytest.raises(ValidationError):
        _estimate(confidence="high")


def test_provider_and_version_metadata() -> None:
    est = _estimate()
    assert est.provider == "SoilGrids"
    assert est.version == "2.0"
    assert "CC BY 4.0" in est.attribution


def test_estimate_is_immutable() -> None:
    est = _estimate()
    with pytest.raises(ValidationError):
        est.lat = 0.0  # type: ignore[misc]
