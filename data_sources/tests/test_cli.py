"""CLI: argument validation, dry run, and a fetch through the injected opener."""

import json
from pathlib import Path

import pytest

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


def test_help_mentions_ontario_example(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["fetch", "--help"])
    assert "Ontario" in capsys.readouterr().out
