"""Validation of the optional field location: one point, in decimal degrees.

Messages are fixed text and never contain the submitted values: a field's coordinates can
identify a farm and must stay out of logs and error reports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

LAT_KEY = "location_lat"
LON_KEY = "location_lon"
CONFIRM_KEY = "confirm_positive_lon"
CONFIRM_ERROR_KEY = "location_lon_confirm"

_STORED = Decimal("0.00001")  # numeric(7,5) / numeric(8,5), migration 0032
_TYPOGRAPHIC_MINUS = chr(0x2212)  # what web pages often show, and copying keeps
_NUMBER = re.compile(r"[+-]?(?:[0-9]{1,3}(?:\.[0-9]*)?|\.[0-9]+)")
_PAIR = re.compile(r"[+-]?[0-9.]+\s*[,;\s]\s*[+-]?[0-9.]+")

MISSING_LAT = "Enter the latitude too, or leave both boxes empty."
MISSING_LON = "Enter the longitude too, or leave both boxes empty."
BAD_LAT = "Enter the latitude in decimal degrees, for example 44.1."
BAD_LON = "Enter the longitude in decimal degrees, for example -80.5."
PAIR = "This box has two numbers. Put the first in Latitude and the second in Longitude."
LAT_RANGE = "Latitude must be between -90 and 90. If this is the longitude, swap the two boxes."
LON_RANGE = "Longitude must be between -180 and 180."
POSITIVE_LON = (
    "This longitude is positive, which means east of Greenwich. Fields in Ontario and the rest "
    "of Canada have a negative longitude, such as -80.5. Add the minus sign and check the two "
    "numbers are not swapped, or tick the box below if it is right."
)


@dataclass(frozen=True)
class Location:
    lat: Decimal
    lon: Decimal

    @property
    def lat_text(self) -> str:
        return format(self.lat, "f")

    @property
    def lon_text(self) -> str:
        return format(self.lon, "f")


def _number(raw: str) -> Decimal | None:
    """The value of a plain decimal; a decimal comma and a typographic minus are accepted."""
    cleaned = raw.replace(_TYPOGRAPHIC_MINUS, "-").replace(",", ".")
    return Decimal(cleaned) if _NUMBER.fullmatch(cleaned) else None


def _coordinate(raw: str, bad: str, limit: int, out_of_range: str) -> tuple[Decimal | None, str]:
    value = _number(raw)
    if value is None:
        return None, PAIR if _PAIR.fullmatch(raw.replace(_TYPOGRAPHIC_MINUS, "-")) else bad
    if abs(value) > limit:
        return None, out_of_range
    return value.quantize(_STORED, rounding=ROUND_HALF_EVEN), ""


def parse_location(
    lat_raw: str, lon_raw: str, *, positive_lon_confirmed: bool
) -> tuple[Location | None, dict[str, str]]:
    """(location, errors). Both empty is valid and gives (None, {}).

    A positive longitude is valid worldwide but usually a lost minus sign here, so it needs
    an explicit confirmation. The sign is never changed for the user.
    """
    lat_raw, lon_raw = lat_raw.strip(), lon_raw.strip()
    if not lat_raw and not lon_raw:
        return None, {}
    errors: dict[str, str] = {}
    lat = lon = None
    if lat_raw:
        lat, message = _coordinate(lat_raw, BAD_LAT, 90, LAT_RANGE)
        if message:
            errors[LAT_KEY] = message
    else:
        errors[LAT_KEY] = MISSING_LAT
    if lon_raw:
        lon, message = _coordinate(lon_raw, BAD_LON, 180, LON_RANGE)
        if message:
            errors[LON_KEY] = message
    else:
        errors[LON_KEY] = MISSING_LON
    if lon is not None and lon > 0 and not positive_lon_confirmed:
        errors[CONFIRM_ERROR_KEY] = POSITIVE_LON
    if errors or lat is None or lon is None:
        return None, errors
    return Location(lat, lon), {}
