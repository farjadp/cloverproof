"""Engine input models (pydantic). Canonical units: t/ha, ha, cm, mg/kg.

Output models live in `results.py`; pack config models in `pack.py`.
"""

import math
from datetime import date
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Crop(StrEnum):
    WHEAT = "wheat"


class WheatClass(StrEnum):
    """Market class of the wheat. A pack may cover only some classes (pack `scope`)."""

    PASTRY = "pastry"  # soft red / soft white
    HARD = "hard"  # hard red / hard white


class ExtractionMethod(StrEnum):
    OLSEN = "olsen"
    BRAY_1 = "bray-1"
    MEHLICH_3 = "mehlich-3"
    # Ammonium acetate extract for exchangeable K (Ontario accredited K test).
    AMMONIUM_ACETATE = "ammonium-acetate"
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
    """One measured value. The extraction method belongs to the value, not the test:
    one lab report can give P by Olsen, K by ammonium acetate and nitrate by KCl.
    """

    form: NutrientForm
    value: NonNegativeFloat
    unit: ConcentrationUnit
    extraction_method: ExtractionMethod
    # Free text naming the method; required when extraction_method is `other`.
    extraction_method_detail: str | None = None

    @model_validator(mode="after")
    def _check_method(self) -> Self:
        detail = (self.extraction_method_detail or "").strip()
        if self.extraction_method is ExtractionMethod.OTHER and not detail:
            raise ValueError("extraction_method_detail is required when extraction_method is other")
        return self

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


class NPrice(_Frozen):
    """N and grain prices behind the N:grain price ratio (rule 5: provenance kept).

    ratio = cost of N (per kg N) / grain price (per kg grain), i.e. kg of grain that
    pay for 1 kg N (Pub 811 Table 4-14 footnote 1). Computed from the two prices; a
    stored ratio that does not match them is rejected.
    """

    n_price_per_kg_n: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    grain_price_per_kg: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    source: str
    price_date: date
    ratio: Annotated[float, Field(gt=0, allow_inf_nan=False)]

    @model_validator(mode="before")
    @classmethod
    def _compute_ratio(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        try:
            n = float(data["n_price_per_kg_n"])
            g = float(data["grain_price_per_kg"])
            computed = n / g
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return data  # field validation reports the problem
        given = data.get("ratio")
        if given is not None and not math.isclose(float(given), computed):
            raise ValueError(f"ratio {given} does not match the prices ({computed:.6g})")
        return {**data, "ratio": computed}

    @field_validator("source")
    @classmethod
    def _source_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("price source must not be empty")
        return cleaned


class RecommendationInput(_Frozen):
    crop: Crop
    target_yield_t_ha: PositiveFloat
    previous_crop: str
    area_ha: PositiveFloat
    plan_date: date
    soil_test: SoilTest | None = None
    # N and grain prices with source and date; the ratio is computed from them. An
    # economic input, not a pack constant. Needed only by N methods that look the rate
    # up by price ratio (e.g. pack ca-on v1).
    n_price: NPrice | None = None
    # Wheat market class. Required by packs whose `scope.wheat_class` is set (ca-on v1:
    # pastry only).
    wheat_class: WheatClass | None = None
    # Was manure (or another organic amendment) applied for this crop? Required by
    # packs whose `scope.manure` is set. True is refused by every pack: the engine
    # has no manure N credit yet.
    manure_applied: bool | None = None

    _OMIT_IF_NONE: ClassVar[tuple[str, ...]] = ("n_price", "wheat_class", "manure_applied")

    @model_serializer(mode="wrap")
    def _omit_absent_optionals(self, handler: SerializerFunctionWrapHandler) -> Any:
        # Leave keys out when absent, so snapshots from engine 0.2.0 inputs match.
        data = handler(self)
        if isinstance(data, dict):
            for name in self._OMIT_IF_NONE:
                if name in data and data[name] is None:
                    del data[name]
        return data

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
