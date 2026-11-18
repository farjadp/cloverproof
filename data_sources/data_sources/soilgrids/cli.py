"""`python -m data_sources.soilgrids fetch ...` — fill the offline SoilGrids cache."""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from data_sources.soilgrids.catalog import (
    ALLOWED_PROPERTIES,
    DEFAULT_DEPTHS,
    REGIONS,
    UnsupportedDepthError,
    UnsupportedPropertyError,
    parse_depths,
    parse_properties,
)
from data_sources.soilgrids.estimate import default_cache_dir
from data_sources.soilgrids.fetch import (
    MAX_BBOX_DEG,
    FetchError,
    Opener,
    bbox_slug,
    default_opener,
    fetch,
    planned_layers,
    planned_size,
    validate_bbox,
)

EXAMPLE = (
    "Ontario cache (operator step, large; see docs/runbook-soilgrids-cache.md):\n"
    "  uv run python -m data_sources.soilgrids fetch --region ontario --dry-run\n"
    "example (small southern Ontario window, about 3 x 4 km):\n"
    "  uv run python -m data_sources.soilgrids fetch --bbox -80.27,43.53,-80.23,43.57 \\\n"
    "      --props phh2o,soc,nitrogen,clay,sand,silt --depths 0-5cm,5-15cm,15-30cm\n"
    "backup (Saskatchewan, Prairies): --bbox -106.70,52.10,-106.66,52.14\n"
    "Data: SoilGrids 2.0, ISRIC - World Soil Information, CC BY 4.0."
)


class _JsonFormatter(logging.Formatter):
    _STD = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message"}

    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "event": record.getMessage()}
        payload.update({k: v for k, v in record.__dict__.items() if k not in self._STD})
        return json.dumps(payload, default=str)


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m data_sources.soilgrids")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser(
        "fetch",
        help="clip SoilGrids layers for a bbox into the local cache",
        epilog=EXAMPLE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    where = f.add_mutually_exclusive_group(required=True)
    where.add_argument("--bbox", help="minlon,minlat,maxlon,maxlat (WGS84 degrees)")
    where.add_argument("--region", choices=sorted(REGIONS), help="named bbox, no size cap")
    f.add_argument(
        "--props",
        default=",".join(ALLOWED_PROPERTIES),
        help=f"comma list from the N-only allowlist: {','.join(ALLOWED_PROPERTIES)}",
    )
    f.add_argument("--depths", default=",".join(DEFAULT_DEPTHS), help="comma list, e.g. 0-5cm")
    f.add_argument("--cache-dir", type=Path, default=None, help="default: data/cache/soilgrids")
    f.add_argument("--dry-run", action="store_true", help="print the plan; open nothing")
    return ap


def _join_bbox(argv: list[str]) -> list[str]:
    """`--bbox -80.27,...` would be read as an option by argparse; glue it to `--bbox=`."""
    out: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--bbox" and i + 1 < len(argv):
            out.append(f"--bbox={argv[i + 1]}")
            i += 2
        else:
            out.append(argv[i])
            i += 1
    return out


def main(
    argv: Sequence[str] | None = None,
    *,
    opener: Opener = default_opener,
    today: date | None = None,
) -> int:
    args = _parser().parse_args(_join_bbox(list(sys.argv[1:] if argv is None else argv)))
    if not logging.getLogger().handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        logging.basicConfig(level=logging.INFO, handlers=[handler])
    try:
        max_deg = None if args.region else MAX_BBOX_DEG
        raw_bbox = REGIONS[args.region] if args.region else args.bbox.split(",")
        bbox = validate_bbox([float(v) for v in raw_bbox], max_deg=max_deg)
        props = parse_properties(args.props)
        depths = parse_depths(args.depths)
    except (UnsupportedPropertyError, UnsupportedDepthError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: invalid --bbox: {exc}", file=sys.stderr)
        return 2
    cache_dir = args.cache_dir or default_cache_dir()
    if args.dry_run:
        plan = planned_layers(props, depths)
        width, height, raw_bytes = planned_size(bbox, len(plan))
        print(f"target: {cache_dir / bbox_slug(bbox)}")
        print(f"bbox: {','.join(str(v) for v in bbox)}")
        print(
            f"estimate: {len(plan)} layers, about {width} x {height} px each, "
            f"about {raw_bytes / 1e9:.1f} GB uncompressed (deflate makes the files smaller)"
        )
        for *_, url in plan:
            print(url)
        return 0
    try:
        out = fetch(
            bbox,
            props,
            depths,
            cache_dir=cache_dir,
            opener=opener,
            today=today,
            max_bbox_deg=max_deg,
        )
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(out / "manifest.json")
    return 0
