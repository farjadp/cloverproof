"""What the soil estimate page shows: wording, number formats, grouping, default season.

Display only, and no I/O. The values come from `repo.soil_estimates`; this page never fetches
anything and nothing here reaches a plan or the engine (ADR 0006, rule 3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from cloverproof_app.repo.soil_estimates import CurrentEstimate, EstimateSeason

STATEMENT = (
    "Modelled estimate, not a lab test. It does not change any rate in a plan,"
    " and it can never produce a P or K recommendation."
)
OPERATOR_NOTE = "An operator loads estimates; nothing is fetched from here."
NO_LOCATION_TITLE = "This field has no location yet."
NO_LOCATION_BODY = "An estimate is looked up for one point in the field."
NOT_LOADED_TITLE = "No estimate is loaded for this field and season."
# The loader stores nothing for a point the cache cannot answer, so the two cases look the same.
NOT_LOADED_BODY = "If a load has already run, the soil map may have no value at this point."
STALE_TITLE = "Older estimates are not tied to this field's present location and are not used."
STALE_BODY = "They are not shown here."
NO_VALUE = "No value loaded for this point."

CONFIDENCE = "low"  # Every SoilGrids value is low confidence (ADR 0006).
VALUE_NOTE = "Modelled mean for this depth"
RANGE_NOTE = "The model's 5\u201395 % range"
RATIO_NOTE = "Uncertainty: range width divided by the median"

PROPERTY_NAMES = (
    ("phh2o", "Soil pH in water"),
    ("soc", "Organic carbon"),
    ("nitrogen", "Total soil nitrogen (not nitrate, not an N credit)"),
    ("clay", "Clay"),
    ("sand", "Sand"),
    ("silt", "Silt"),
)
SOURCE_NAMES = {"soilgrids": "SoilGrids"}
# The precision SoilGrids publishes in each canonical unit (ADR 0006 conversions).
UNIT_DIGITS = {"pH": 1, "%": 1, "mg/kg": 0}


@dataclass(frozen=True)
class EstimateRow:
    depth: str
    value: str | None = None
    range: str | None = None
    ratio: str | None = None
    source: str = ""
    resolution: str = ""
    retrieved: str = ""


@dataclass(frozen=True)
class PropertyGroup:
    name: str
    rows: list[EstimateRow]


@dataclass(frozen=True)
class Credit:
    attribution: str
    citation: str
    licence: str


def amount(value: Decimal, unit: str) -> str:
    return f"{value:,.{UNIT_DIGITS.get(unit, 1)}f}"


def ratio_text(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def depth_text(top_cm: int, bottom_cm: int) -> str:
    return f"{top_cm}\u2013{bottom_cm} cm"


def range_text(e: CurrentEstimate) -> str | None:
    if e.value_q05 is None or e.value_q95 is None:
        return None
    return f"{amount(e.value_q05, e.unit)}\u2013{amount(e.value_q95, e.unit)} {e.unit}"


def estimate_row(e: CurrentEstimate) -> EstimateRow:
    return EstimateRow(
        depth=depth_text(e.depth_top_cm, e.depth_bottom_cm),
        value=f"{amount(e.value, e.unit)} {e.unit}",
        range=range_text(e),
        ratio=ratio_text(e.uncertainty_ratio) if e.uncertainty_ratio is not None else None,
        source=f"{SOURCE_NAMES.get(e.source, e.source)} {e.source_version}",
        resolution=f"{e.resolution_m.normalize():f} m",
        retrieved=e.retrieved_on.isoformat(),
    )


def property_groups(estimates: Sequence[CurrentEstimate]) -> list[PropertyGroup]:
    """Every property, in a fixed order, with a row per loaded depth; a gap stays visible."""
    if not estimates:
        return []
    depths = sorted({(e.depth_top_cm, e.depth_bottom_cm) for e in estimates})
    groups = []
    for prop, name in PROPERTY_NAMES:
        found = {(e.depth_top_cm, e.depth_bottom_cm): e for e in estimates if e.property == prop}
        rows = []
        if found:
            rows = [
                estimate_row(found[d]) if d in found else EstimateRow(depth=depth_text(*d))
                for d in depths
            ]
        groups.append(PropertyGroup(name, rows))
    return groups


def credits_of(estimates: Sequence[CurrentEstimate]) -> list[Credit]:
    """Each distinct credit once, exactly as stored; normally there is one (CC BY, ADR 0006)."""
    return list(dict.fromkeys(Credit(e.attribution, e.citation, e.licence) for e in estimates))


def default_season(seasons: Sequence[EstimateSeason], today: date) -> EstimateSeason | None:
    """Newest season with usable values, else one with older rows (so the warning shows), else
    this calendar year's, else the newest. `seasons` is newest first."""
    for season in seasons:
        if season.has_current:
            return season
    for season in seasons:
        if season.has_estimates:
            return season
    for season in seasons:
        if season.label == str(today.year):
            return season
    return seasons[0] if seasons else None


def find_season(seasons: Sequence[EstimateSeason], season_id: UUID) -> EstimateSeason | None:
    return next((s for s in seasons if s.id == season_id), None)


def season_option(season: EstimateSeason) -> str:
    if season.has_current:
        return f"{season.label} (estimates loaded)"
    if season.has_estimates:
        return f"{season.label} (estimates out of date)"
    return season.label
