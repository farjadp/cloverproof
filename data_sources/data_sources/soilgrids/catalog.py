"""What we may read from SoilGrids, where it lives, and how to convert it.

Every unit factor below comes from ISRIC's "SoilGrids layers" documentation page
(table "Properties": divide the mapped value by the conversion factor to get the
conventional unit). Verified 2026-11-16 against the page as archived on 2026-02-08;
docs.isric.org itself did not answer from our network that day.
"""

from dataclasses import dataclass
from typing import Final, Literal, get_args

ISRIC_LAYERS_DOC: Final = "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html"
ISRIC_ACCESS_DOC: Final = "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html"

# Public WebDAV/HTTP file tree: <base>/<prop>/<prop>_<depth>_<stat>.vrt
DEFAULT_BASE_URL: Final = "https://files.isric.org/soilgrids/latest/data"
SOILGRIDS_VERSION: Final = "2.0"
SOURCE_NAME: Final = "SoilGrids"
LICENSE: Final = "CC BY 4.0"
# Attribution string exactly as docs/data-sources.md requires it.
ATTRIBUTION: Final = "SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0"
# Volume, pages and DOI as in docs/data-sources.md. First author per Crossref metadata for
# this DOI (checked 2026-11-18); the docs row says "de Sousa et al. (author order to verify)".
CITATION: Final = "Poggio et al. 2021, SOIL 7, 217-240, doi:10.5194/soil-7-217-2021"

# Ontario's extreme points, rounded outwards to 0.1 degree. A bounding box, not the
# provincial boundary: it also covers parts of Manitoba, Quebec, Nunavut and the US.
ONTARIO_BBOX: Final = (-95.2, 41.6, -74.3, 56.9)
REGIONS: Final[dict[str, tuple[float, float, float, float]]] = {"ontario": ONTARIO_BBOX}

# SoilGrids SRS: Interrupted Goode Homolosine on WGS84 (ESRI:54052; ISRIC pseudo-code
# EPSG:152160). Source: ISRIC_ACCESS_DOC, "How can I use the Homolosine projection?".
HOMOLOSINE_PROJ4: Final = "+proj=igh +datum=WGS84 +no_defs +towgs84=0,0,0"

# Hard allowlist (CLAUDE.md rule 3: estimates are N-only; P/K need a lab test).
Property = Literal["phh2o", "soc", "nitrogen", "clay", "sand", "silt"]
ALLOWED_PROPERTIES: Final[tuple[str, ...]] = get_args(Property)

Depth = Literal["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]
STANDARD_DEPTHS: Final[tuple[str, ...]] = get_args(Depth)
DEFAULT_DEPTHS: Final = ("0-5cm", "5-15cm", "15-30cm")

# Layers ISRIC publishes per property/depth (file suffixes as listed on files.isric.org;
# the docs page writes "Q05" but the real files are "Q0.05"). Q0.5 is not fetched.
Statistic = Literal["mean", "Q0.05", "Q0.95", "uncertainty"]
STATISTICS: Final[tuple[str, ...]] = get_args(Statistic)

_FORBIDDEN_URL_PARTS = ("rest.isric.org", "properties/query")

_PK_HINTS = ("phosph", "potass", "p2o5", "k2o", "olsen", "bray", "mehlich")


class UnsupportedPropertyError(ValueError):
    pass


class UnsupportedDepthError(ValueError):
    pass


@dataclass(frozen=True)
class Conversion:
    mapped_unit: str
    divide_by: float  # ISRIC "Conversion Factor": conventional = mapped / divide_by
    conventional_unit: str
    # SI prefix step from the ISRIC conventional unit to our canonical unit (CLAUDE.md
    # rule 7: concentrations in mg/kg). 1 g/kg = 1000 mg/kg; not an agronomic constant.
    si_multiplier: float
    canonical_unit: str
    source_url: str
    verified: bool

    def to_canonical(self, mapped: float) -> float:
        return mapped / self.divide_by * self.si_multiplier


# Factors: ISRIC SoilGrids layers table, https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html
CONVERSIONS: Final[dict[str, Conversion]] = {
    # phh2o: mapped "pH x 10", factor 10 -> pH. Source: ISRIC_LAYERS_DOC
    "phh2o": Conversion("pH*10", 10, "pH", 1, "pH", ISRIC_LAYERS_DOC, True),
    # soc: mapped dg/kg, factor 10 -> g/kg; x1000 -> mg/kg. Source: ISRIC_LAYERS_DOC
    "soc": Conversion("dg/kg", 10, "g/kg", 1000, "mg/kg", ISRIC_LAYERS_DOC, True),
    # nitrogen (total N): mapped cg/kg, factor 100 -> g/kg; x1000 -> mg/kg. Source: ISRIC_LAYERS_DOC
    "nitrogen": Conversion("cg/kg", 100, "g/kg", 1000, "mg/kg", ISRIC_LAYERS_DOC, True),
    # clay/sand/silt: mapped g/kg, factor 10 -> g/100g (%). Source: ISRIC_LAYERS_DOC
    "clay": Conversion("g/kg", 10, "%", 1, "%", ISRIC_LAYERS_DOC, True),
    "sand": Conversion("g/kg", 10, "%", 1, "%", ISRIC_LAYERS_DOC, True),
    "silt": Conversion("g/kg", 10, "%", 1, "%", ISRIC_LAYERS_DOC, True),
}

# Uncertainty layer = (Q0.95 - Q0.05) / Q0.50, stored x10 as integer -> divide by 10,
# dimensionless ratio. Source: ISRIC_LAYERS_DOC, section "Uncertainty layer".
UNCERTAINTY_FACTOR: Final = Conversion("ratio*10", 10, "ratio", 1, "ratio", ISRIC_LAYERS_DOC, True)


def _is_pk(name: str) -> bool:
    n = name.lower()
    return n in {"p", "k"} or any(h in n for h in _PK_HINTS)


def parse_properties(raw: str | tuple[str, ...] | list[str]) -> tuple[str, ...]:
    items = raw.split(",") if isinstance(raw, str) else list(raw)
    out: list[str] = []
    for item in (i.strip() for i in items):
        if not item:
            continue
        if _is_pk(item):
            raise UnsupportedPropertyError(
                f"'{item}': phosphorus/potassium are never taken from SoilGrids estimates "
                "(N-only rule, CLAUDE.md rule 3: P/K need a lab soil test)."
            )
        if item not in ALLOWED_PROPERTIES:
            raise UnsupportedPropertyError(
                f"'{item}' is not allowed (N-only allowlist: {', '.join(ALLOWED_PROPERTIES)})."
            )
        if item not in out:
            out.append(item)
    if not out:
        raise UnsupportedPropertyError("no properties given")
    return tuple(out)


def parse_depths(raw: str | tuple[str, ...] | list[str]) -> tuple[str, ...]:
    items = raw.split(",") if isinstance(raw, str) else list(raw)
    out: list[str] = []
    for item in (i.strip() for i in items):
        if not item:
            continue
        if item not in STANDARD_DEPTHS:
            raise UnsupportedDepthError(
                f"'{item}' is not a SoilGrids depth ({', '.join(STANDARD_DEPTHS)})."
            )
        if item not in out:
            out.append(item)
    if not out:
        raise UnsupportedDepthError("no depths given")
    return tuple(out)


def depth_bounds_cm(depth: str) -> tuple[int, int]:
    top, bottom = depth.removesuffix("cm").split("-")
    return int(top), int(bottom)


def layer_name(prop: str, depth: str, stat: str) -> str:
    return f"{prop}_{depth}_{stat}"


def layer_url(prop: str, depth: str, stat: str, *, base_url: str = DEFAULT_BASE_URL) -> str:
    if any(part in base_url for part in _FORBIDDEN_URL_PARTS):
        raise ValueError("the SoilGrids REST API is never used; read the file tree instead")
    parse_properties((prop,))
    parse_depths((depth,))
    if stat not in STATISTICS:
        raise ValueError(f"unknown statistic '{stat}'")
    return f"{base_url.rstrip('/')}/{prop}/{layer_name(prop, depth, stat)}.vrt"
