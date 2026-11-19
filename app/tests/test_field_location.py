"""Field location form rules (no database)."""

from decimal import Decimal

import pytest

from cloverproof_app import field_location as fl


def parse(lat: str, lon: str, confirmed: bool = False):  # type: ignore[no-untyped-def]
    return fl.parse_location(lat, lon, positive_lon_confirmed=confirmed)


def test_both_empty_means_no_location() -> None:
    assert parse("", "  ") == (None, {})


@pytest.mark.parametrize(
    ("lat", "lon", "want_lat", "want_lon"),
    [
        ("12.5", "-34.25", "12.50000", "-34.25000"),
        ("12,5", "-34,25", "12.50000", "-34.25000"),
        ("+12.5", chr(0x2212) + "34.25", "12.50000", "-34.25000"),
        ("12.1234567", "-34.7654321", "12.12346", "-34.76543"),
        ("90", "-180", "90.00000", "-180.00000"),
        ("-90", "0", "-90.00000", "0.00000"),
    ],
)
def test_valid_values(lat: str, lon: str, want_lat: str, want_lon: str) -> None:
    location, errors = parse(lat, lon)
    assert errors == {} and location is not None
    assert (location.lat_text, location.lon_text) == (want_lat, want_lon)
    assert isinstance(location.lat, Decimal)


@pytest.mark.parametrize(
    ("lat", "lon", "key", "message"),
    [
        ("12.5", "", fl.LON_KEY, fl.MISSING_LON),
        ("", "-34.5", fl.LAT_KEY, fl.MISSING_LAT),
        ("abc", "-34.5", fl.LAT_KEY, fl.BAD_LAT),
        ("12.5", "34 W", fl.LON_KEY, fl.BAD_LON),
        ("NaN", "-34.5", fl.LAT_KEY, fl.BAD_LAT),
        ("12.5", "Infinity", fl.LON_KEY, fl.BAD_LON),
        ("1e1", "-34.5", fl.LAT_KEY, fl.BAD_LAT),
        ("12.5, -34.5", "", fl.LAT_KEY, fl.PAIR),
        ("90.000001", "-34.5", fl.LAT_KEY, fl.LAT_RANGE),
        ("-91", "-34.5", fl.LAT_KEY, fl.LAT_RANGE),
        ("12.5", "-180.000001", fl.LON_KEY, fl.LON_RANGE),
        ("12.5", "181", fl.LON_KEY, fl.LON_RANGE),
    ],
)
def test_errors(lat: str, lon: str, key: str, message: str) -> None:
    location, errors = parse(lat, lon)
    assert location is None and errors[key] == message


def test_positive_longitude_warns_and_is_not_flipped() -> None:
    assert parse("12.5", "34.5") == (None, {fl.CONFIRM_ERROR_KEY: fl.POSITIVE_LON})
    location, errors = parse("12.5", "34.5", confirmed=True)
    assert errors == {} and location is not None and location.lon == Decimal("34.50000")


def test_messages_never_repeat_the_values() -> None:
    _, errors = parse("77.77777", "188.88888")
    assert errors and not any("77.7" in m or "188.8" in m for m in errors.values())
