"""Country-pack config models. Packs hold every agronomic number; code holds none.

Parsing takes an already-loaded mapping (`parse_pack`); file reading lives in
`loaders.py` so calculation code never does I/O.
"""

import math
from collections.abc import Iterator
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from cloverproof_engine.models import Crop


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ConstantStatus(StrEnum):
    PLACEHOLDER = "PLACEHOLDER"
    VALIDATED = "VALIDATED"


class PackConstant(_Frozen):
    value: float = Field(allow_inf_nan=False)
    unit: str
    status: ConstantStatus
    source: str | None

    @model_validator(mode="after")
    def _check_label(self) -> Self:
        if self.status is ConstantStatus.PLACEHOLDER and self.source is not None:
            raise ValueError("a PLACEHOLDER constant must have source: null")
        if self.status is ConstantStatus.VALIDATED and not (self.source or "").strip():
            raise ValueError("a VALIDATED constant needs a source")
        return self

    @property
    def is_placeholder(self) -> bool:
        return self.status is ConstantStatus.PLACEHOLDER


def _unit(expected: str) -> AfterValidator:
    def check(c: PackConstant) -> PackConstant:
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
Fraction = Annotated[PackConstant, _unit("fraction"), AfterValidator(_fraction_open_closed)]
TPerHa = Annotated[PackConstant, _unit("t/ha"), AfterValidator(_positive)]
Years = Annotated[PackConstant, _unit("years"), AfterValidator(_positive)]


class PreviousCrop(_Frozen):
    label: str = Field(min_length=1)
    credit: KgNPerHa


class SplitSpec(_Frozen):
    stage_label: str = Field(min_length=1)
    fraction: Fraction


class NitrogenConfig(_Frozen):
    method: str = Field(min_length=1)
    n_uptake_per_t_grain: KgNPerT
    soil_n_supply: KgNPerHa
    fertilizer_n_efficiency: Fraction
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
    nitrogen: NitrogenConfig
    confidence: ConfidenceConfig


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

    def iter_constants(self) -> Iterator[PackConstant]:
        yield from _walk(self)

    @property
    def has_placeholders(self) -> bool:
        return any(c.is_placeholder for c in self.iter_constants())


def _walk(node: Any) -> Iterator[PackConstant]:
    if isinstance(node, PackConstant):
        yield node
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
