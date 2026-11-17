"""Estimate schema. N-only by construction: there is no field that can hold P or K."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from data_sources.soilgrids.catalog import ATTRIBUTION, SOILGRIDS_VERSION, Depth, Property

_STRICT = ConfigDict(extra="forbid", frozen=True)


class EstimateValue(BaseModel):
    """One property at one depth at one point, from the cached `mean` layer."""

    model_config = _STRICT

    property: Property
    depth: Depth
    depth_top_cm: int = Field(ge=0)
    depth_bottom_cm: int = Field(gt=0)
    statistic: Literal["mean"]
    value: float = Field(allow_inf_nan=False)
    unit: str
    mapped_value: int  # raw integer as stored by SoilGrids, kept for audit
    mapped_unit: str
    conversion_factor_source: str
    q05: float | None = Field(default=None, allow_inf_nan=False)
    q95: float | None = Field(default=None, allow_inf_nan=False)
    uncertainty_ratio: float | None = Field(default=None, allow_inf_nan=False)
    url: str
    retrieved_on: date
    resolution_m: float = Field(gt=0)


class SoilEstimate(BaseModel):
    """Modelled soil properties at a point. Never a lab test; never high/medium confidence."""

    model_config = _STRICT

    source: Literal["estimate"] = "estimate"
    provider: Literal["SoilGrids"] = "SoilGrids"
    version: Literal["2.0"] = SOILGRIDS_VERSION
    confidence: Literal["low"] = "low"
    attribution: str = ATTRIBUTION
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    values: tuple[EstimateValue, ...] = Field(min_length=1)
