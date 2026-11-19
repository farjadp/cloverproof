"""`soil-estimate-load`: cached SoilGrids values into soil_estimate, no network, tiny rasters."""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest

from cloverproof_app import cli
from cloverproof_app.repo import soil_estimates
from cloverproof_engine.models import SoilEstimate, SoilEstimateValue

from .conftest import Org, as_owner, as_role, insert, locate_field, use_context

np = pytest.importorskip("numpy")
rasterio = pytest.importorskip("rasterio")
rasterio_crs = pytest.importorskip("rasterio.crs")
rasterio_transform = pytest.importorskip("rasterio.transform")
rasterio_warp = pytest.importorskip("rasterio.warp")
catalog = pytest.importorskip("data_sources.soilgrids.catalog")

pytestmark = pytest.mark.db

# Synthetic point (the one the data_sources tests use) and a second one in the same clip.
LAT, LON = 43.55, -80.25
MOVED_LAT, MOVED_LON = 43.56, -80.24
OUTSIDE_LAT, OUTSIDE_LON = 45.0, -78.0
RETRIEVED = date(2026, 11, 16)
OPERATOR = "agro-a@example.org"
MAPPED = {
    "nitrogen": {"mean": 150, "Q0.05": 80, "Q0.95": 300, "uncertainty": 15},
    "phh2o": {"mean": 65, "Q0.05": 55, "Q0.95": 75, "uncertainty": 3},
}
DEPTHS = ("0-5cm", "5-15cm")
NODATA = -32768
SIZE = 60
PIXEL_M = 250.0
ROW_COUNT = len(MAPPED) * len(DEPTHS)


def write_cache(root: Path, *, masked: bool = False) -> Path:
    """A one-clip cache in the layout `fetch` writes; every pixel is nodata if `masked`."""
    clip = root / "bbox_test"
    clip.mkdir(parents=True)
    crs = rasterio_crs.CRS.from_proj4(catalog.HOMOLOSINE_PROJ4)
    xs, ys = rasterio_warp.transform("EPSG:4326", crs, [LON], [LAT])
    transform = rasterio_transform.from_origin(
        xs[0] - SIZE / 2 * PIXEL_M, ys[0] + SIZE / 2 * PIXEL_M, PIXEL_M, PIXEL_M
    )
    layers = []
    for prop, stats in MAPPED.items():
        for depth in DEPTHS:
            for stat, value in stats.items():
                name = f"{prop}_{depth}_{stat}.tif"
                with rasterio.open(
                    clip / name, "w", driver="GTiff", height=SIZE, width=SIZE, count=1,
                    dtype="int16", crs=crs, transform=transform, nodata=NODATA,
                ) as dst:  # fmt: skip
                    fill = NODATA if masked else value
                    dst.write(np.full((SIZE, SIZE), fill, dtype="int16"), 1)
                layers.append(
                    {
                        "property": prop,
                        "depth": depth,
                        "statistic": stat,
                        "file": name,
                        "url": catalog.layer_url(prop, depth, stat),
                        "resolution_m": [PIXEL_M, PIXEL_M],
                    }
                )
    manifest = {
        "source": catalog.SOURCE_NAME,
        "version": catalog.SOILGRIDS_VERSION,
        "retrieved_on": RETRIEVED.isoformat(),
        "bbox_wgs84": [LON - 0.02, LAT - 0.02, LON + 0.02, LAT + 0.02],
        "layers": layers,
    }
    (clip / "manifest.json").write_text(json.dumps(manifest))
    return root


@pytest.fixture(scope="module")
def cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_cache(tmp_path_factory.mktemp("soilgrids"))


@pytest.fixture(autouse=True)
def local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV", raising=False)


def load(db: psycopg.Connection, org: Org, cache_dir: Path, **overrides: Any) -> Any:
    values: dict[str, Any] = {
        "field_id": org.fields[0],
        "season_id": org.season,
        "cache_dir": cache_dir,
        "operator_email": OPERATOR,
        "hosted": False,
    }
    return cli.soil_estimate_load(db, **(values | overrides))


def command(db: psycopg.Connection, field: UUID, season: UUID, cache_dir: Path, email: str) -> str:
    args = cli.build_parser().parse_args(
        [
            "soil-estimate-load",
            "--field", str(field),
            "--season", str(season),
            "--cache-dir", str(cache_dir),
            "--as", email,
        ]
    )  # fmt: skip
    return cli.run_command(db, args)


def stored_count(db: psycopg.Connection, org: Org) -> int:
    use_context(db, org.agronomist, org.id)
    row = db.execute("select count(*) from soil_estimate").fetchone()
    assert row is not None
    return int(row[0])


def current(db: psycopg.Connection, org: Org) -> list[soil_estimates.CurrentEstimate]:
    use_context(db, org.agronomist, org.id)
    return soil_estimates.current_estimates(db, org.id, org.fields[0], org.season)


def stale(db: psycopg.Connection, org: Org) -> bool:
    use_context(db, org.agronomist, org.id)
    return soil_estimates.has_stale_estimates(db, org.id, org.fields[0], org.season)


def demo_field(db: psycopg.Connection, org: Org, kind: str = "demo") -> UUID:
    with as_owner(db):
        farmer = insert(
            db, "farmer", organisation_id=org.id, display_name="Synthetic", record_kind=kind
        )
        farm = insert(db, "farm", organisation_id=org.id, farmer_id=farmer, name="Synthetic")
        field = insert(db, "field", organisation_id=org.id, farm_id=farm, name="Synthetic")
    locate_field(db, org.id, field, LAT, LON)
    return field


def assert_no_coordinates(text: str) -> None:
    for number in ("43.5", "80.2", "45.0", "78.0"):
        assert number not in text


# --- Happy path -------------------------------------------------------------------------------


def test_load_stores_every_value_with_full_metadata(
    db: psycopg.Connection, org_a: Org, cache: Path
) -> None:
    revision = locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    result = load(db, org_a, cache)
    assert (result.stored, result.revision, result.no_estimate_reason) == (
        ROW_COUNT,
        revision,
        None,
    )

    rows = current(db, org_a)
    assert [(r.property, r.depth) for r in rows] == [
        ("nitrogen", "0-5cm"),
        ("nitrogen", "5-15cm"),
        ("phh2o", "0-5cm"),
        ("phh2o", "5-15cm"),
    ]
    n = rows[0]
    assert (n.value, n.unit) == (Decimal("1500"), "mg/kg")
    assert (n.value_q05, n.value_q95, n.uncertainty_ratio) == (
        Decimal("800"),
        Decimal("3000"),
        Decimal("1.5"),
    )
    assert (n.source, n.source_version, n.resolution_m) == ("soilgrids", "2.0", Decimal("250"))
    assert (n.depth_top_cm, n.depth_bottom_cm, n.statistic) == (0, 5, "mean")
    assert n.retrieved_at == datetime(2026, 11, 16, tzinfo=UTC)
    assert n.retrieved_on == RETRIEVED
    assert n.licence == "CC BY 4.0"
    assert n.attribution == catalog.ATTRIBUTION
    assert n.citation == catalog.CITATION
    assert n.layer_url == catalog.layer_url("nitrogen", "0-5cm", "mean")
    assert n.field_location_revision == revision
    assert rows[2].value == Decimal("6.5")
    assert not stale(db, org_a)

    author = db.execute("select distinct created_by from soil_estimate").fetchall()
    assert author == [(org_a.agronomist,)]


def test_loaded_rows_build_the_engine_input(
    db: psycopg.Connection, org_a: Org, cache: Path
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    load(db, org_a, cache)
    rows = current(db, org_a)
    built = SoilEstimate(
        provider="SoilGrids",
        version="2.0",
        attribution=rows[0].attribution,
        citation=rows[0].citation,
        values=[
            SoilEstimateValue(
                property=r.property,
                depth=r.depth,
                value=float(r.value),
                unit=r.unit,
                statistic=r.statistic,
                q05=float(r.value_q05),
                q95=float(r.value_q95),
                uncertainty_ratio=float(r.uncertainty_ratio),
                url=r.layer_url,
                resolution_m=float(r.resolution_m),
                retrieved_on=r.retrieved_on,
            )
            for r in rows
        ],
    )
    assert len(built.values) == ROW_COUNT


def test_command_reports_without_coordinates_and_stores_none(
    db: psycopg.Connection, org_a: Org, cache: Path
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    message = command(db, org_a.fields[0], org_a.season, cache, OPERATOR)
    assert f"stored {ROW_COUNT} estimate value(s)" in message
    assert_no_coordinates(message.replace(str(org_a.fields[0]), "").replace(str(org_a.season), ""))

    use_context(db, org_a.agronomist, org_a.id)
    rows = db.execute("select to_jsonb(se)::text from soil_estimate se").fetchall()
    assert len(rows) == ROW_COUNT
    for (text,) in rows:
        for number in ("43.55", "80.25"):
            assert number not in text


# --- Nothing to store --------------------------------------------------------------------------


def test_point_outside_the_cache_stores_nothing_and_says_why(
    db: psycopg.Connection, org_a: Org, cache: Path
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], OUTSIDE_LAT, OUTSIDE_LON)
    message = command(db, org_a.fields[0], org_a.season, cache, OPERATOR)
    assert message == "no estimate stored: the field's point is outside the cached area"
    assert stored_count(db, org_a) == 0


def test_masked_pixel_stores_nothing_and_says_why(
    db: psycopg.Connection, org_a: Org, tmp_path: Path
) -> None:
    masked = write_cache(tmp_path / "masked", masked=True)
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    result = load(db, org_a, masked)
    assert result.stored == 0
    assert result.no_estimate_reason is not None and "masked" in result.no_estimate_reason
    assert stored_count(db, org_a) == 0


def test_no_location_is_refused(db: psycopg.Connection, org_a: Org, cache: Path) -> None:
    with pytest.raises(cli.CliError, match="no location"):
        load(db, org_a, cache)
    assert stored_count(db, org_a) == 0


def test_missing_cache_is_a_plain_error_without_the_point(
    db: psycopg.Connection, org_a: Org, tmp_path: Path
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    with pytest.raises(cli.CliError, match="cache could not be read") as caught:
        load(db, org_a, tmp_path / "absent")
    assert_no_coordinates(str(caught.value))


def test_cache_error_text_never_reaches_the_message(
    db: psycopg.Connection, org_a: Org, cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def leaky(lon: float, lat: float, **_: Any) -> None:
        raise RuntimeError(f"failed at ({lon}, {lat})")

    monkeypatch.setattr(cli, "_soilgrids_lookup", lambda: (leaky, "CC BY 4.0"))
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    with pytest.raises(cli.CliError) as caught:
        load(db, org_a, cache)
    assert_no_coordinates(str(caught.value))
    assert caught.value.__suppress_context__ and caught.value.__cause__ is None


def test_missing_data_sources_package_is_a_plain_error(
    db: psycopg.Connection, org_a: Org, cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "data_sources.soilgrids", None)
    with pytest.raises(cli.CliError, match="operator checkout"):
        load(db, org_a, cache)


# --- Who may run it ----------------------------------------------------------------------------


def test_other_org_operator_is_denied(
    db: psycopg.Connection, org_a: Org, org_b: Org, cache: Path
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    with pytest.raises(cli.CliError, match="no such field"):
        load(db, org_a, cache, operator_email="agro-b@example.org")
    assert stored_count(db, org_a) == 0
    assert current(db, org_b) == []


def test_season_of_another_org_is_refused(
    db: psycopg.Connection, org_a: Org, org_b: Org, cache: Path
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    with pytest.raises(cli.CliError, match="no such season"):
        load(db, org_a, cache, season_id=org_b.season)


@pytest.mark.parametrize(
    ("change", "message"),
    [("actor_kind = 'service'", "service account"), ("disabled_at = now()", "disabled")],
)
def test_operator_must_be_an_enabled_human(
    db: psycopg.Connection, org_a: Org, cache: Path, change: str, message: str
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    with as_owner(db):
        db.execute(f"update app_user set {change} where id = %s", (org_a.agronomist,))  # type: ignore[arg-type]
    with pytest.raises(cli.CliError, match=message):
        load(db, org_a, cache)


def test_unknown_operator_is_refused(db: psycopg.Connection, org_a: Org, cache: Path) -> None:
    with pytest.raises(cli.CliError, match="no user"):
        load(db, org_a, cache, operator_email="nobody@example.org")


def test_loader_works_as_the_cli_login_role(
    db: psycopg.Connection, org_a: Org, cache: Path
) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    with as_role(db, "cp_admin"):
        assert load(db, org_a, cache).stored == ROW_COUNT


# --- Hosted safety (ADR 0009) ------------------------------------------------------------------


@pytest.mark.parametrize("env", ["staging", "production", " Production "])
def test_real_farmer_is_refused_when_deployed(
    db: psycopg.Connection,
    org_a: Org,
    cache: Path,
    monkeypatch: pytest.MonkeyPatch,
    env: str,
) -> None:
    monkeypatch.setenv("ENV", env)
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    with pytest.raises(cli.CliError, match="real farmer"):
        command(db, org_a.fields[0], org_a.season, cache, OPERATOR)
    assert stored_count(db, org_a) == 0


@pytest.mark.parametrize("kind", ["demo", "reference"])
def test_synthetic_farmer_loads_when_deployed(
    db: psycopg.Connection,
    org_a: Org,
    cache: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    monkeypatch.setenv("ENV", "staging")
    field = demo_field(db, org_a, kind)
    assert "stored" in command(db, field, org_a.season, cache, OPERATOR)
    assert stored_count(db, org_a) == ROW_COUNT


def test_hosted_load_refuses_a_login_that_skips_rls(
    db: psycopg.Connection, org_a: Org, cache: Path
) -> None:
    field = demo_field(db, org_a)
    with pytest.raises(cli.CliError, match="cp_app_login"), as_owner(db):
        load(db, org_a, cache, field_id=field, hosted=True)


@pytest.mark.parametrize(
    ("env", "host", "hosted"),
    [
        ("", "127.0.0.1", False),
        ("development", "localhost", False),
        ("development", "/var/run/postgresql", False),
        ("staging", "127.0.0.1", True),
        ("PRODUCTION", "localhost", True),
        # A remote database is hosted even if the shell lacks ENV or says development.
        ("", "db.example.org", True),
        ("development", "db.example.org", True),
    ],
)
def test_hosted_target(env: str, host: str, hosted: bool) -> None:
    assert cli.is_hosted_target(env, host) is hosted


def test_runbook_marks_a_staging_farmer_as_demo(db: psycopg.Connection, org_a: Org) -> None:
    """The steps in docs/runbook-soilgrids-cache.md: cp_admin login, superadmin context."""
    with as_owner(db):
        db.execute(
            "update app_user set platform_role = 'superadmin' where id = %s", (org_a.agronomist,)
        )
    farmer = insert(db, "farmer", organisation_id=org_a.id, display_name="Synthetic")
    with as_role(db, "cp_admin"):
        use_context(db, org_a.agronomist, org_a.id)
        db.execute("update farmer set record_kind = 'demo' where id = %s", (farmer,))
    row = db.execute("select record_kind from farmer where id = %s", (farmer,)).fetchone()
    assert row == ("demo",)


# --- Moves --------------------------------------------------------------------------------------


def test_move_then_reload(db: psycopg.Connection, org_a: Org, cache: Path) -> None:
    first = locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    load(db, org_a, cache)

    with pytest.raises(cli.CliError, match="already stored"):
        load(db, org_a, cache)
    assert stored_count(db, org_a) == ROW_COUNT

    moved = locate_field(db, org_a.id, org_a.fields[0], MOVED_LAT, MOVED_LON)
    assert moved == first + 1
    assert current(db, org_a) == []
    assert stale(db, org_a)

    # Same cache, same retrieval date, new location.
    assert load(db, org_a, cache).revision == moved
    assert {r.field_location_revision for r in current(db, org_a)} == {moved}
    assert len(current(db, org_a)) == ROW_COUNT
    assert not stale(db, org_a)
    assert stored_count(db, org_a) == 2 * ROW_COUNT


def test_clearing_then_load_is_refused(db: psycopg.Connection, org_a: Org, cache: Path) -> None:
    locate_field(db, org_a.id, org_a.fields[0], LAT, LON)
    load(db, org_a, cache)
    use_context(db, org_a.agronomist, org_a.id)
    db.execute(
        "update field set location_lat = null, location_lon = null where id = %s",
        (org_a.fields[0],),
    )
    assert current(db, org_a) == []
    assert stale(db, org_a)
    with pytest.raises(cli.CliError, match="no location"):
        load(db, org_a, cache)
