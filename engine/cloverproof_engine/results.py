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
from cloverproof_engine.models import ProductForm
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
    # PLACEHOLDER unless the whole pack is validated (a window has no label of its own).
    status: ConstantStatus
    # Where the wording comes from, with its `basis`. Not a validation (rule 9).
    citation: Citation | None = None


class UsedProductRule(_Frozen):
    """A pack product rule a decision relied on, copied with its label."""

    path: str
    value: str
    status: ConstantStatus
    source: str | None


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
