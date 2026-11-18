"""Engine input models (pydantic). Canonical units: t/ha, ha, cm, mg/kg.

Output models live in `results.py`; pack config models in `pack.py`.
"""

import math
from datetime import date
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
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
    # Always given; null states that the report names no method. The field cannot be
    # left out. P and K are then refused: no method means no table to read (rule 7).
    extraction_method: ExtractionMethod | None
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


class ProductForm(StrEnum):
    GRANULAR = "granular"
    LIQUID = "liquid"


GradePercent = Annotated[float, Field(ge=0, allow_inf_nan=False)]
ProductText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProductInput(_Frozen):
    """One catalog product, prepared by the caller. Label facts only, nothing commercial.

    Grades are label percentages with the form in the name (rule 7): N and S elemental,
    P as P2O5, K as K2O. `s_pct` is required, so an unknown sulphur content is never
    read as zero. Only products the caller considers usable (active) belong here.
    """

    id: ProductText
    name: ProductText
    n_pct: GradePercent
    p2o5_pct: GradePercent
    k2o_pct: GradePercent
    s_pct: GradePercent
    form: ProductForm
    # Required for a liquid, absent for a granular product (as in the catalog).
    density_kg_per_l: PositiveFloat | None = None
    grade_source: ProductText

    @model_validator(mode="after")
    def _check(self) -> Self:
        # Imported here: units.py imports this module.
        from cloverproof_engine import units

        grades = (self.n_pct, self.p2o5_pct, self.k2o_pct, self.s_pct)
        if not units.grades_fit_in_product(grades):
            raise ValueError(f"product grades add up to more than {units.PERCENT} %")
        is_liquid = self.form is ProductForm.LIQUID
        if is_liquid and self.density_kg_per_l is None:
            raise ValueError("a liquid product needs density_kg_per_l")
        if not is_liquid and self.density_kg_per_l is not None:
            raise ValueError("a granular product must not have density_kg_per_l")
        return self


SoilEstimateProperty = Literal["phh2o", "soc", "nitrogen", "clay", "sand", "silt"]
SoilEstimateDepth = Literal["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]

# Canonical unit of each SoilGrids property, as `data_sources` delivers it.
SOIL_ESTIMATE_UNITS: dict[str, str] = {
    "phh2o": "pH",
    "soc": "mg/kg",
    "nitrogen": "mg/kg",
    "clay": "%",
    "sand": "%",
    "silt": "%",
}

# The licence SoilGrids 2.0 is published under; its attribution must name it.
SOIL_ESTIMATE_LICENCE = "CC BY 4.0"
SOIL_ESTIMATE_LAYER_BASE = "https://files.isric.org/soilgrids/latest/data"

# Kept exactly as supplied (licence wording), so it is checked but never stripped.
VerbatimText = Annotated[str, Field(pattern=r"\S")]


class SoilEstimateValue(_Frozen):
    """One modelled SoilGrids value (the `mean` layer) at one depth, with its provenance.

    The property allowlist has no P or K, and `nitrogen` is total N: there is no field
    for a nutrient form, so it cannot be read as nitrate (rules 3 and 7).
    """

    property: SoilEstimateProperty
    depth: SoilEstimateDepth
    value: NonNegativeFloat
    unit: str
    statistic: Literal["mean"]
    q05: NonNegativeFloat | None = None
    q95: NonNegativeFloat | None = None
    uncertainty_ratio: NonNegativeFloat | None = None
    # Exactly the published address of this value's layer, so it can carry no field
    # location (rule 12).
    url: str
    resolution_m: PositiveFloat
    retrieved_on: date

    @model_validator(mode="after")
    def _check(self) -> Self:
        # Imported here: units.py imports this module.
        from cloverproof_engine import units

        expected = SOIL_ESTIMATE_UNITS[self.property]
        if self.unit != expected:
            raise ValueError(f"{self.property} must be in {expected}, got {self.unit}")
        layer = f"{self.property}/{self.property}_{self.depth}_{self.statistic}.vrt"
        if self.url != f"{SOIL_ESTIMATE_LAYER_BASE}/{layer}":
            raise ValueError("url must be the published address of this value's own layer")
        if (self.q05 is None) != (self.q95 is None):
            raise ValueError("q05 and q95 must be given together")
        if self.q05 is not None and self.q95 is not None and self.q05 > self.q95:
            raise ValueError("q05 must not be greater than q95")
        # Each value only. Clay, sand and silt are separate layers of separately rounded
        # integers and `data_sources` does not close them, so their sum can pass 100.
        scale_max = units.UNIT_SCALE_MAX.get(self.unit)
        if scale_max is not None:
            for name, number in (("value", self.value), ("q05", self.q05), ("q95", self.q95)):
                if number is not None and number > scale_max:
                    raise ValueError(f"{name} is above the {self.unit} scale ({scale_max:g})")
        return self


class SoilEstimate(_Frozen):
    """Modelled soil properties for the field, prepared by the caller from `data_sources`.

    Context only: never a lab test, never a source of a P or K rate, and no pack rule
    reads it. It reaches the input snapshot with its version and retrieval dates (rule 5).
    """

    provider: Literal["SoilGrids"]
    version: Literal["2.0"]
    attribution: VerbatimText
    citation: VerbatimText
    values: list[SoilEstimateValue] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        keys = [(v.property, v.depth) for v in self.values]
        if len(keys) != len(set(keys)):
            raise ValueError("each property may appear only once per depth")
        if SOIL_ESTIMATE_LICENCE not in self.attribution:
            raise ValueError(f"attribution must name the licence ({SOIL_ESTIMATE_LICENCE})")
        return self


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
    # Catalog products to match the N lines against. None = matching not requested;
    # an empty list = requested, and the catalog has nothing to offer.
    products: list[ProductInput] | None = None
    # Modelled soil properties, shown as low-confidence context. Changes no number.
    soil_estimate: SoilEstimate | None = None

    _OMIT_IF_NONE: ClassVar[tuple[str, ...]] = (
        "n_price",
        "wheat_class",
        "manure_applied",
        "products",
        "soil_estimate",
    )

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
        products = self.products or []
        if len({p.id for p in products}) != len(products):
            raise ValueError("product id values must be unique")
        if len({p.name.casefold() for p in products}) != len(products):
            raise ValueError("product name values must be unique (ignoring case)")
        return self
