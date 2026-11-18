"""Engine output models. Every number is an `ExplainedNumber`."""

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
)

from cloverproof_engine.confidence import Confidence, ConfidenceRuleHit
from cloverproof_engine.models import ExtractionMethod, NutrientForm, ProductForm
from cloverproof_engine.pack import Citation, ConstantStatus, PackConstant


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExplainedNumber(_Frozen):
    name: str
    value: float
    unit: str
    explanation: str
    # True when any pack constant feeding this number (directly or through an
    # earlier step) is PLACEHOLDER. Set explicitly by the method; no default.
    uses_placeholder: bool


class UsedConstant(_Frozen):
    """A pack constant a method actually used, copied with its label."""

    path: str
    value: float
    unit: str
    status: ConstantStatus
    source: str | None

    @classmethod
    def of(cls, path: str, constant: PackConstant) -> "UsedConstant":
        return cls(
            path=path,
            value=constant.value,
            unit=constant.unit,
            status=constant.status,
            source=constant.source,
        )

    @property
    def is_placeholder(self) -> bool:
        return self.status is ConstantStatus.PLACEHOLDER


class TimingWindow(_Frozen):
    """When a split is applied, as the pack words it. No dates: the pack gives none."""

    label: str
    # Always PLACEHOLDER until the pack gives a window its own status and source.
    status: ConstantStatus
    # Where the wording comes from, with its `basis`. Not a validation (rule 9).
    citation: Citation | None = None


class UsedProductRule(_Frozen):
    """A pack product rule a decision relied on, copied with its label."""

    path: str
    value: str
    status: ConstantStatus
    source: str | None
    # Where the rule comes from, with its `basis`. Not a validation (rule 9).
    citation: Citation | None = None


class ProductGrade(_Frozen):
    """Label grade in %, each with its explicit form (rule 7)."""

    n: ExplainedNumber  # % N
    p2o5: ExplainedNumber  # % P2O5
    k2o: ExplainedNumber  # % K2O
    s: ExplainedNumber  # % S


class ProductMatch(_Frozen):
    """The catalog product that carries this line's N, and how much of it."""

    matched: Literal[True] = True
    product_id: str
    product_name: str
    form: ProductForm
    grade: ProductGrade
    grade_source: str
    selection: Literal["pack_preference", "single_fit"]
    rate: ExplainedNumber  # kg product/ha
    total: ExplainedNumber  # kg product for the field
    volume_rate: ExplainedNumber | None = None  # L product/ha, liquids only
    sulphur_rate: ExplainedNumber | None = None  # kg S/ha the product brings along
    rules_used: list[UsedProductRule]
    explanation: str


class ProductNotMatched(_Frozen):
    """The line stays nutrient-only; `explanation` says why. No product is implied."""

    matched: Literal[False] = False
    code: Literal[
        "no_products",
        "no_n_needed",
        "none_fit",
        "no_choice_rule",
        "several_fit",
        "single_fit_not_allowed",
        "quantity_out_of_range",  # the grade, density or area gives no usable number
        "rate_edited",  # set when an agronomist's edit changes the line's N rate
    ]
    # Products that fit but were not selected, sorted by name. Not a ranking.
    fitting_products: list[str]
    rules_used: list[UsedProductRule]
    explanation: str


class SplitApplication(_Frozen):
    """One application line. `splits` always holds at least one.

    `timing_window` and `explanation` arrived in engine 0.4.0; the defaults keep
    documents stored by older engines loadable. `timing_window` is None when the pack
    defines no split plan: the engine does not invent a timing.

    `product_match` arrived in engine 0.5.0. It is None, and left out of the document,
    when the input has no `products`. Its quantities derive from this line's `rate`:
    whoever edits that rate in a copy of the document must recompute or drop them.
    """

    stage_label: str
    fraction: ExplainedNumber
    rate: ExplainedNumber
    total: ExplainedNumber
    timing_window: TimingWindow | None = None
    # Why this line exists and where its timing comes from. Quotes no rate, so it stays
    # true when an agronomist edits the numbers in a copy of the document.
    explanation: str = ""
    product_match: (
        Annotated[ProductMatch | ProductNotMatched, Field(discriminator="matched")] | None
    ) = None

    @model_serializer(mode="wrap")
    def _omit_absent_match(self, handler: SerializerFunctionWrapHandler) -> Any:
        data = handler(self)
        if isinstance(data, dict) and data.get("product_match") is None:
            data.pop("product_match", None)
        return data


class NutrientResult(_Frozen):
    nutrient: Literal["N"]
    method_id: str
    rate: ExplainedNumber
    total: ExplainedNumber
    components: list[ExplainedNumber]
    splits: list[SplitApplication]
    bound_applied: Literal["min", "max"] | None
    # Every pack constant this calculation used, in order of use. Unused pack
    # entries (e.g. credits for other previous crops) are not listed.
    constants_used: list[UsedConstant]


class FormAmount(_Frozen):
    """A number with the nutrient form it is expressed in (rule 7)."""

    form: NutrientForm
    amount: ExplainedNumber


class PkRecommended(_Frozen):
    """A P or K rate read from the pack table for the soil test's extraction method.

    Every amount is given as the element and as the oxide. `rate_form` says which of the
    two the pack table states; the other is converted through `units.py`.
    """

    outcome: Literal["recommended"] = "recommended"
    nutrient: Literal["P", "K"]
    method_id: str
    extraction_method: ExtractionMethod
    soil_test_elemental: FormAmount  # mg/kg
    soil_test_oxide: FormAmount  # mg/kg
    table_band: str
    response: str
    response_label: str
    rate_form: NutrientForm
    rate_elemental: FormAmount  # kg/ha
    rate_oxide: FormAmount  # kg/ha
    total_elemental: FormAmount  # kg for the field
    total_oxide: FormAmount  # kg for the field
    constants_used: list[UsedConstant]


class PkRefused(_Frozen):
    """No rate for this nutrient; `explanation` names what is missing."""

    outcome: Literal["refused"] = "refused"
    nutrient: Literal["P", "K"]
    code: Literal[
        "no_lab_test",
        "no_pack_guidance",
        "no_soil_test_value",
        "no_extraction_method",
        "no_table_for_method",
        "sample_depth_mismatch",
        "outside_table",
    ]
    explanation: str


PkLine = Annotated[PkRecommended | PkRefused, Field(discriminator="outcome")]


class PkResults(_Frozen):
    phosphorus: PkLine
    potassium: PkLine

    @property
    def lines(self) -> tuple[PkRecommended | PkRefused, PkRecommended | PkRefused]:
        return (self.phosphorus, self.potassium)


class Note(_Frozen):
    code: str
    text: str


class Recommendation(_Frozen):
    engine_version: str
    pack_id: str
    pack_version: str
    pack_status: str
    # SHA-256 of the canonical parsed pack (cloverproof_engine.pack.pack_sha256).
    pack_sha256: str
    crop: str
    nitrogen: NutrientResult
    phosphorus_potassium: Note
    notes: list[Note]
    confidence: Confidence
    confidence_reasons: list[ConfidenceRuleHit]
    input_snapshot: dict[str, Any]
    # Since engine 0.6.0. Only for a lab soil test with a P or K value under a pack with
    # P/K tables; otherwise None and left out of the document. Not plan lines yet.
    phosphorus_potassium_rates: PkResults | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_pk_rates(self, handler: SerializerFunctionWrapHandler) -> Any:
        data = handler(self)
        if isinstance(data, dict) and data.get("phosphorus_potassium_rates") is None:
            data.pop("phosphorus_potassium_rates", None)
        return data
