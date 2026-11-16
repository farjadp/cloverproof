"""Engine input models (pydantic). Canonical units: t/ha, ha, cm, mg/kg.

Output models live in `results.py`; pack config models in `pack.py`.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Crop(StrEnum):
    WHEAT = "wheat"


class ExtractionMethod(StrEnum):
    OLSEN = "olsen"
    BRAY_1 = "bray-1"
    MEHLICH_3 = "mehlich-3"
    OTHER = "other"


class SoilTestSource(StrEnum):
    LAB = "lab"
    ESTIMATE = "estimate"


class NutrientForm(StrEnum):
    """Form a value is expressed in. Elemental vs oxide is always explicit."""

    N = "N"
    NO3_N = "NO3-N"
    P = "P"
    P2O5 = "P2O5"
    K = "K"
    K2O = "K2O"


class ConcentrationUnit(StrEnum):
    MG_PER_KG = "mg/kg"
    PPM = "ppm"


PositiveFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegativeFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]

_NUTRIENT_OF_FORM: dict[NutrientForm, str] = {
    NutrientForm.N: "N",
    NutrientForm.NO3_N: "N",
    NutrientForm.P: "P",
    NutrientForm.P2O5: "P",
    NutrientForm.K: "K",
    NutrientForm.K2O: "K",
}


def nutrient_of(form: NutrientForm) -> str:
    """The element a form expresses: "N", "P" or "K"."""
    return _NUTRIENT_OF_FORM[form]


class SoilTestValue(_Frozen):
    form: NutrientForm
    value: NonNegativeFloat
    unit: ConcentrationUnit

    @property
    def nutrient(self) -> str:
        return nutrient_of(self.form)

    @property
    def value_mg_per_kg(self) -> float:
        # ppm by mass and mg/kg are identical; both units are accepted, stored as given.
        return self.value


class SoilTest(_Frozen):
    sample_date: date
    depth_top_cm: NonNegativeFloat
    depth_bottom_cm: PositiveFloat
    extraction_method: ExtractionMethod
    source: SoilTestSource
    lab: str | None = None
    values: list[SoilTestValue] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.depth_bottom_cm <= self.depth_top_cm:
            raise ValueError("depth_bottom_cm must be greater than depth_top_cm")
        nutrients = [v.nutrient for v in self.values]
        if len(nutrients) != len(set(nutrients)):
            raise ValueError("each nutrient may appear only once (in one form)")
        return self

    def value_for(self, nutrient: str) -> SoilTestValue | None:
        return next((v for v in self.values if v.nutrient == nutrient), None)


class RecommendationInput(_Frozen):
    crop: Crop
    target_yield_t_ha: PositiveFloat
    previous_crop: str
    area_ha: PositiveFloat
    plan_date: date
    soil_test: SoilTest | None = None

    @field_validator("previous_crop")
    @classmethod
    def _normalise_previous_crop(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("previous_crop must not be empty")
        return cleaned

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.soil_test is not None and self.soil_test.sample_date > self.plan_date:
            raise ValueError("soil test sample_date is after plan_date")
        return self
