"""Engine output models. Every number is an `ExplainedNumber`."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from cloverproof_engine.confidence import Confidence, ConfidenceRuleHit


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExplainedNumber(_Frozen):
    name: str
    value: float
    unit: str
    explanation: str


class SplitApplication(_Frozen):
    stage_label: str
    fraction: ExplainedNumber
    rate: ExplainedNumber
    total: ExplainedNumber


class NutrientResult(_Frozen):
    nutrient: Literal["N"]
    method_id: str
    rate: ExplainedNumber
    total: ExplainedNumber
    components: list[ExplainedNumber]
    splits: list[SplitApplication]
    bound_applied: Literal["min", "max"] | None


class Note(_Frozen):
    code: str
    text: str


class Recommendation(_Frozen):
    engine_version: str
    pack_id: str
    pack_version: str
    pack_status: str
    crop: str
    nitrogen: NutrientResult
    phosphorus_potassium: Note
    notes: list[Note]
    confidence: Confidence
    confidence_reasons: list[ConfidenceRuleHit]
    input_snapshot: dict[str, Any]
