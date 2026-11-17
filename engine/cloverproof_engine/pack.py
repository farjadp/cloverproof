"""Country-pack config models. Packs hold every agronomic number; code holds none.

Parsing takes an already-loaded mapping (`parse_pack`); file reading lives in
`loaders.py` so calculation code never does I/O.

Pack fingerprint (`pack_sha256`): SHA-256 of the *parsed, validated* pack in
canonical JSON, not of the YAML bytes. Canonical form = `Pack.model_dump(mode="json")`
serialised with sorted keys, no whitespace (separators "," and ":"), UTF-8,
ensure_ascii off. Consequences: comments, YAML layout, mapping key order and
int-vs-float spelling (30 vs 30.0) do not change the hash; any value, unit,
status, source, label, description, method id or list order (e.g. splits) does.
Optional fields added after engine 0.2.0 (`citation`, `soil_test_methods`) are left
out of the canonical form when absent, so packs that do not use them keep their
fingerprint.

Labels (CLAUDE.md rule 9): every constant is `PLACEHOLDER` (`source: null`) until a
human agronomist validates it (`VALIDATED` + `source`). A constant taken from a
published document carries a `citation` and stays `PLACEHOLDER`: a citation says
where a number was read, not that it was validated.
"""

import hashlib
import itertools
import json
import math
from collections.abc import Iterator
from datetime import date
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
    model_serializer,
    model_validator,
)

from cloverproof_engine.models import ConcentrationUnit, Crop, ExtractionMethod, NutrientForm

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Optional fields dropped from dumps when None (keeps older pack fingerprints).
    _OMIT_IF_NONE: ClassVar[tuple[str, ...]] = ()

    @model_serializer(mode="wrap")
    def _omit_none(self, handler: SerializerFunctionWrapHandler) -> Any:
        data = handler(self)
        if isinstance(data, dict):
            for name in self._OMIT_IF_NONE:
                if name in data and data[name] is None:
                    del data[name]
        return data


class ConstantStatus(StrEnum):
    PLACEHOLDER = "PLACEHOLDER"
    VALIDATED = "VALIDATED"


class CitationBasis(StrEnum):
    """How a cited value relates to the document.

    - `stated`: the document states this value; explanations say "read from".
    - `derived`: computed by the engine from stated values (e.g. a table maximum).
    - `inferred`: concluded by the engine from what the document says or omits.
    Derived and inferred values are never presented as "read from" the source.
    """

    STATED = "stated"
    DERIVED = "derived"
    INFERRED = "inferred"


class Citation(_Frozen):
    """Where a number comes from: a published document, entered by hand.

    Not a validation: a cited constant stays PLACEHOLDER (rule 9). `basis` is
    required; a `derived` or `inferred` citation needs a `note` saying how.
    """

    _OMIT_IF_NONE = ("note",)

    title: NonBlankStr
    publisher: NonBlankStr
    year: int = Field(gt=0)
    locator: NonBlankStr  # page / table / figure
    url: NonBlankStr
    accessed_on: date
    basis: CitationBasis
    note: str | None = None

    @model_validator(mode="after")
    def _check_note(self) -> Self:
        if self.basis is not CitationBasis.STATED and not (self.note or "").strip():
            raise ValueError(f"a {self.basis.value} citation needs a note saying how")
        return self

    def short(self) -> str:
        return f"{self.title}, {self.locator}"


def _check_label(status: ConstantStatus, source: str | None) -> None:
    if status is ConstantStatus.PLACEHOLDER and source is not None:
        raise ValueError("a PLACEHOLDER constant must have source: null")
    if status is ConstantStatus.VALIDATED and not (source or "").strip():
        raise ValueError("a VALIDATED constant needs a source")


class PackConstant(_Frozen):
    _OMIT_IF_NONE = ("citation",)

    value: float = Field(allow_inf_nan=False)
    unit: str
    status: ConstantStatus
    source: str | None
    citation: Citation | None = None

    @model_validator(mode="after")
    def _check_label(self) -> Self:
        _check_label(self.status, self.source)
        return self

    @property
    def is_placeholder(self) -> bool:
        return self.status is ConstantStatus.PLACEHOLDER


class UnsetConstant(_Frozen):
    """A constant whose value is not known yet (`value: null`). Always PLACEHOLDER.

    Allowed only where the engine can refuse cleanly (previous-crop credits): a
    method that needs it raises instead of guessing.
    """

    _OMIT_IF_NONE = ("citation",)

    value: None
    unit: str
    status: Literal[ConstantStatus.PLACEHOLDER]
    source: None
    citation: Citation | None = None

    @property
    def is_placeholder(self) -> bool:
        return True


def _unit(expected: str) -> AfterValidator:
    def check(c: PackConstant) -> PackConstant:
        if c.unit != expected:
            raise ValueError(f"unit must be {expected!r}, got {c.unit!r}")
        return c

    return AfterValidator(check)


def _unset_unit(expected: str) -> AfterValidator:
    def check(c: UnsetConstant) -> UnsetConstant:
        if c.unit != expected:
            raise ValueError(f"unit must be {expected!r}, got {c.unit!r}")
        return c

    return AfterValidator(check)


def _non_negative(c: PackConstant) -> PackConstant:
    if c.value < 0:
        raise ValueError("must be >= 0")
    return c


def _positive(c: PackConstant) -> PackConstant:
    if c.value <= 0:
        raise ValueError("must be > 0")
    return c


def _fraction_open_closed(c: PackConstant) -> PackConstant:
    if not 0 < c.value <= 1:
        raise ValueError("must be in (0, 1]")
    return c


KgNPerT = Annotated[PackConstant, _unit("kg N/t"), AfterValidator(_non_negative)]
KgNPerHa = Annotated[PackConstant, _unit("kg N/ha"), AfterValidator(_non_negative)]
UnsetKgNPerHa = Annotated[UnsetConstant, _unset_unit("kg N/ha")]
Fraction = Annotated[PackConstant, _unit("fraction"), AfterValidator(_fraction_open_closed)]
TPerHa = Annotated[PackConstant, _unit("t/ha"), AfterValidator(_positive)]
Years = Annotated[PackConstant, _unit("years"), AfterValidator(_positive)]


class PreviousCrop(_Frozen):
    _OMIT_IF_NONE = ("needs_input",)

    label: str = Field(min_length=1)
    # `value: null` (UnsetConstant) = credit not known yet; the method refuses.
    credit: KgNPerHa | UnsetKgNPerHa
    # For an unset credit: the input the engine would need to set it (shown in
    # the refusal message).
    needs_input: NonBlankStr | None = None


class SplitSpec(_Frozen):
    _OMIT_IF_NONE = ("timing_citation",)

    stage_label: str = Field(min_length=1)
    fraction: Fraction
    # Where the timing in `stage_label` comes from (the fraction cites itself).
    timing_citation: Citation | None = None


class _NitrogenBase(_Frozen):
    """Fields every nitrogen method shares (the concierge tool reads these)."""

    min_rate: KgNPerHa
    max_rate: KgNPerHa
    previous_crop_credits: dict[str, PreviousCrop] = Field(min_length=1)
    splits: list[SplitSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.min_rate.value > self.max_rate.value:
            raise ValueError("min_rate must not exceed max_rate")
        if not math.isclose(sum(s.fraction.value for s in self.splits), 1.0):
            raise ValueError("split fractions must sum to 1")
        for key in self.previous_crop_credits:
            if key != key.strip().lower() or not key:
                raise ValueError(f"previous crop key {key!r} must be lower-case, trimmed")
        return self


class MassBalanceNitrogen(_NitrogenBase):
    method: Literal["n_mass_balance"]
    n_uptake_per_t_grain: KgNPerT
    soil_n_supply: KgNPerHa
    fertilizer_n_efficiency: Fraction


def _strictly_increasing_positive(values: list[float]) -> list[float]:
    if any(v <= 0 for v in values):
        raise ValueError("axis values must be > 0")
    if any(b <= a for a, b in itertools.pairwise(values)):
        raise ValueError("axis values must be strictly increasing")
    return values


Axis = Annotated[
    list[Annotated[float, Field(allow_inf_nan=False)]],
    Field(min_length=1),
    AfterValidator(_strictly_increasing_positive),
]


class NRateTable(_Frozen):
    """N rate by expected yield (columns) and N:grain price ratio (rows).

    One label for the whole table (status / source / citation), as the table is
    read from one source. `rates[i][j]` is the rate at `price_ratio[i]`,
    `yield_t_ha[j]`. Price ratio = cost of N ($/kg N) / grain price ($/kg grain),
    i.e. kg of grain that pay for 1 kg N.
    """

    _OMIT_IF_NONE = ("citation",)

    unit: Literal["kg N/ha"]
    status: ConstantStatus
    source: str | None
    citation: Citation | None = None
    yield_t_ha: Axis
    price_ratio: Axis
    rates: list[list[Annotated[float, Field(ge=0, allow_inf_nan=False)]]]

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_label(self.status, self.source)
        if len(self.rates) != len(self.price_ratio):
            raise ValueError("rates needs one row per price ratio")
        if any(len(row) != len(self.yield_t_ha) for row in self.rates):
            raise ValueError("each rates row needs one value per yield")
        return self

    def cell(self, i: int, j: int) -> PackConstant:
        """The rate at price_ratio[i], yield_t_ha[j], with the table's label."""
        return PackConstant(
            value=self.rates[i][j],
            unit=self.unit,
            status=self.status,
            source=self.source,
            citation=self.citation,
        )

    def cells(self) -> Iterator[PackConstant]:
        for i in range(len(self.price_ratio)):
            for j in range(len(self.yield_t_ha)):
                yield self.cell(i, j)


class YieldPriceTableNitrogen(_NitrogenBase):
    method: Literal["n_yield_price_table"]
    rate_table: NRateTable


NitrogenConfig = Annotated[
    MassBalanceNitrogen | YieldPriceTableNitrogen, Field(discriminator="method")
]


class SoilTestMethodSpec(_Frozen):
    """The soil test a pack's P or K guidance is calibrated for."""

    _OMIT_IF_NONE = ("extraction_method_detail", "citation")

    form: NutrientForm
    unit: ConcentrationUnit
    extraction_method: ExtractionMethod
    extraction_method_detail: str | None = None
    citation: Citation | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.form not in (NutrientForm.P, NutrientForm.K):
            raise ValueError("soil-test P and K are given as the element (P or K)")
        detail = (self.extraction_method_detail or "").strip()
        if self.extraction_method is ExtractionMethod.OTHER and not detail:
            raise ValueError("extraction_method_detail is required when extraction_method is other")
        return self


class ConfidenceConfig(_Frozen):
    target_yield_min: TPerHa
    target_yield_max: TPerHa
    max_soil_test_age_years: Years

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.target_yield_min.value >= self.target_yield_max.value:
            raise ValueError("target_yield_min must be below target_yield_max")
        return self


class CropConfig(_Frozen):
    _OMIT_IF_NONE = ("soil_test_methods",)

    nitrogen: NitrogenConfig
    confidence: ConfidenceConfig
    # Declarative in engine 0.3.0: which test the pack's P/K guidance assumes.
    # P/K rates arrive in S3 (still only with a lab soil test, rule 3).
    soil_test_methods: dict[Literal["P", "K"], SoilTestMethodSpec] | None = None

    @model_validator(mode="after")
    def _check_methods(self) -> Self:
        for nutrient, spec in (self.soil_test_methods or {}).items():
            if spec.form.value != nutrient:
                raise ValueError(f"soil_test_methods.{nutrient} must have form {nutrient}")
        return self


class Pack(_Frozen):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    status: Literal["placeholder", "validated"]
    description: str = ""
    crops: dict[Crop, CropConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.status == "validated" and self.has_placeholders:
            raise ValueError("a validated pack must not contain PLACEHOLDER constants")
        return self

    def iter_constants(self) -> Iterator[PackConstant | UnsetConstant]:
        """Every constant, including each table cell and every not-set value."""
        yield from _walk(self)

    @property
    def has_placeholders(self) -> bool:
        return any(c.is_placeholder for c in self.iter_constants())

    @property
    def unset_constants(self) -> int:
        """How many constants have no value yet (`value: null`)."""
        return sum(isinstance(c, UnsetConstant) for c in self.iter_constants())


def _walk(node: Any) -> Iterator[PackConstant | UnsetConstant]:
    if isinstance(node, PackConstant | UnsetConstant):
        yield node
    elif isinstance(node, NRateTable):
        yield from node.cells()
    elif isinstance(node, BaseModel):
        for name in type(node).model_fields:
            yield from _walk(getattr(node, name))
    elif isinstance(node, dict):
        for child in node.values():
            yield from _walk(child)
    elif isinstance(node, list):
        for child in node:
            yield from _walk(child)


def parse_pack(data: dict[str, Any]) -> Pack:
    """Validate an already-loaded pack mapping."""
    return Pack.model_validate(data)


def canonical_pack_json(pack: Pack) -> str:
    """Deterministic JSON of the parsed pack (see module docstring)."""
    return json.dumps(
        pack.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def pack_sha256(pack: Pack) -> str:
    """Hex SHA-256 of `canonical_pack_json(pack)`. Recorded on every recommendation."""
    return hashlib.sha256(canonical_pack_json(pack).encode("utf-8")).hexdigest()
