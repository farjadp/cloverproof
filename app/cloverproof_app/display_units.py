"""Which units the plan page shows numbers in: a display preference, nothing else.

Stored documents, snapshots and `recommendation_line` stay canonical (CLAUDE.md rule 7):
this module only computes what a template prints, and never produces a value to save. The
choice lives in a cookie until account preferences arrive with S9. Typed values and the
proof PDF do not pass through here.

All factors come from `cloverproof_engine.units`. It has no bushel or gallon factor, so
yield and liquid volume stay metric; field area stays in hectares.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request

from cloverproof_engine import units

COOKIE = "cp_display_units"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # seconds; how long the choice is remembered
METRIC = "metric"
IMPERIAL = "imperial"
SYSTEMS = frozenset({METRIC, IMPERIAL})

# What a stored unit may name. Anything else ("kg N/t", "L product/ha", "%") stays as stored.
_SUBSTANCES = ("N", "P", "P2O5", "K", "K2O", "S", "product")


def _kg_to_lb(value: float) -> float:
    # units.py has no public kg -> lb function; its exact pound definition is the only source.
    return value / units._KG_PER_LB


_CONVERSIONS: dict[str, tuple[str, Callable[[float], float]]] = {
    **{f"kg {s}/ha": (f"lb {s}/ac", units.kg_per_ha_to_lb_per_ac) for s in _SUBSTANCES},
    **{f"kg {s}": (f"lb {s}", _kg_to_lb) for s in _SUBSTANCES},
}


@dataclass(frozen=True)
class Shown:
    value: float
    unit: str


def from_request(request: Request) -> str:
    """The visitor's choice; metric when the cookie is absent or not one of the two values."""
    value = request.cookies.get(COOKIE)
    return value if value in SYSTEMS else METRIC


def convert(value: float, unit: str, system: str) -> Shown | None:
    """`value` for display in `system`; None means show the stored number as it is."""
    if system != IMPERIAL or unit not in _CONVERSIONS:
        return None
    shown_unit, factor = _CONVERSIONS[unit]
    return Shown(factor(float(value)), shown_unit)


def detail_text(detail: str, system: str) -> str:
    """The diff's line caption, which names the unit of the numbers beside it."""
    if system != IMPERIAL:
        return detail
    return detail.replace("(kg N/ha)", "(lb N/ac, stored as kg N/ha)")
