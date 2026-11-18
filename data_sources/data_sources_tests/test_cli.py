"""CLI: argument validation, dry run, and a fetch through the injected opener."""

import json
from pathlib import Path

import pytest

from data_sources.soilgrids import NoEstimate, SoilEstimate, lookup_estimate
from data_sources.soilgrids.cli import main

BBOX_ARG = "-80.27,43.53,-80.23,43.57"


@pytest.mark.parametrize("prop", ["phosphorus", "potassium", "p", "k"])
def test_cli_rejects_p_and_k(prop: str, capsys, tmp_path: Path) -> None:
    code = main(
        ["fetch", "--bbox", BBOX_ARG, "--props", f"nitrogen,{prop}", "--cache-dir", str(tmp_path)]
    )
    assert code == 2
    err = capsys.readouterr().err
    assert "N-only" in err
    assert not list(tmp_path.iterdir())


def test_cli_rejects_bad_bbox(capsys, tmp_path: Path) -> None:
    code = main(["fetch", "--bbox", "1,2,3", "--cache-dir", str(tmp_path)])
    assert code == 2
    assert "bbox" in capsys.readouterr().err


def test_cli_dry_run_opens_nothing(capsys, tmp_path: Path) -> None:
    def boom(url: str):
        raise AssertionError(f"dry run opened {url}")

    code = main(
        [
            "fetch",
            "--bbox",
            BBOX_ARG,
            "--props",
            "soc",
            "--depths",
            "0-5cm",
            "--dry-run",
            "--cache-dir",
            str(tmp_path),
        ],
        opener=boom,
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "https://files.isric.org/soilgrids/latest/data/soc/soc_0-5cm_mean.vrt" in out
    assert not list(tmp_path.iterdir())


def test_cli_fetch_with_injected_opener(sg, opener, tmp_path: Path, capsys) -> None:
    code = main(
        [
            "fetch",
            "--bbox",
            BBOX_ARG,
            "--props",
            "nitrogen",
            "--depths",
            "0-5cm",
            "--cache-dir",
            str(tmp_path),
        ],
        opener=opener,
        today=sg.RETRIEVED,
    )
    assert code == 0
    manifests = list(tmp_path.rglob("manifest.json"))
    assert len(manifests) == 1
    assert len(json.loads(manifests[0].read_text())["layers"]) == 4


def test_ontario_dry_run_prints_the_plan_and_opens_nothing(capsys, tmp_path: Path) -> None:
    def boom(url: str):
        raise AssertionError(f"dry run opened {url}")

    code = main(
        ["fetch", "--region", "ontario", "--dry-run", "--cache-dir", str(tmp_path)], opener=boom
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "bbox: -95.2,41.6,-74.3,56.9" in out
    assert "estimate: 72 layers, about 7283 x 6434 px each, about 6.7 GB uncompressed" in out
    urls = [line for line in out.splitlines() if line.startswith("https://")]
    assert len(urls) == 72
    assert all(u.startswith("https://files.isric.org/soilgrids/latest/data/") for u in urls)
    assert not any("rest.isric.org" in u for u in urls)
    assert not list(tmp_path.iterdir())


def test_ontario_fetch_then_lookup_inside_and_outside(sg, opener, tmp_path: Path) -> None:
    args = ["fetch", "--region", "ontario", "--props", "nitrogen", "--depths", "0-5cm"]
    code = main([*args, "--cache-dir", str(tmp_path)], opener=opener, today=sg.RETRIEVED)
    assert code == 0
    inside = lookup_estimate(sg.POINT_LON, sg.POINT_LAT, cache_dir=tmp_path)
    assert isinstance(inside, SoilEstimate)
    assert lookup_estimate(-100.0, 50.0, cache_dir=tmp_path) == NoEstimate(reason="outside_cache")


def test_region_and_bbox_are_exclusive(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["fetch", "--region", "ontario", "--bbox", BBOX_ARG, "--cache-dir", str(tmp_path)])


def test_explicit_bbox_keeps_the_size_cap(capsys, tmp_path: Path) -> None:
    code = main(["fetch", "--bbox", "-95.2,41.6,-74.3,56.9", "--cache-dir", str(tmp_path)])
    assert code == 2
    assert "larger than" in capsys.readouterr().err


def test_help_mentions_ontario_example(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["fetch", "--help"])
    assert "Ontario" in capsys.readouterr().out
