"""Common fertilizer types that can pre-fill the product form on /products.

`data/product_presets.yaml` holds published, cited values that no human has validated
(CLAUDE.md rule 9: PLACEHOLDER, TODO(agronomist)). A preset only fills an editable form: nothing
here writes to the database. The file is checked when it is loaded, so a bad edit stops the app
at startup instead of reaching the form.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

PRESETS_PATH = Path(__file__).parent / "data" / "product_presets.yaml"
GROUPS = ("Nitrogen", "Phosphate", "Potash", "Sulphur", "Blended liquids")
FORMS = ("granular", "liquid")
NAME_MAX = 200
SOURCE_MAX = 500
GRADE_PLACES = 2  # numeric(5,2)
DENSITY_PLACES = 3  # numeric(6,3)
DENSITY_MAX = Decimal("999.999")
QUERY_MAX = 100

GRADE_FIELDS = ("n", "p2o5", "k2o", "s")
# Ends every preset citation. Activation asks for the label actually checked when it is there.
UNCONFIRMED_SOURCE = "unconfirmed, check the product label"
TEXT_FIELDS = ("slug", "name", "group", "form", "source", "url", "printed", "notes")
FIELDS = frozenset((*TEXT_FIELDS, *GRADE_FIELDS, "density_kg_per_l"))
KEY = re.compile(r"[a-z0-9_]+")


class PresetError(ValueError):
    """The preset file breaks a rule."""


def plain_number(value: Decimal) -> str:
    """10.50 -> 10.5, 100.00 -> 100 (never scientific notation)."""
    return format(value.normalize(), "f")


def decimal_places(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    group: str
    n: Decimal
    p2o5: Decimal
    k2o: Decimal
    s: Decimal | None  # None: the source states no figure. Never read this as 0.
    form: str
    density_kg_per_l: Decimal | None
    source: str
    url: str
    printed: str
    notes: str

    @property
    def grade(self) -> str:
        """N-P2O5-K2O, plus S only when the source states it."""
        parts = [self.n, self.p2o5, self.k2o] + ([self.s] if self.s is not None else [])
        return "-".join(plain_number(part) for part in parts)

    @property
    def needs_density(self) -> bool:
        return self.form == "liquid" and self.density_kg_per_l is None

    def form_values(self) -> dict[str, str]:
        """Text for the form. An unknown value stays empty so a person must enter it."""

        def shown(value: Decimal | None) -> str:
            return "" if value is None else plain_number(value)

        return {
            "name": self.name,
            "n": shown(self.n),
            "p2o5": shown(self.p2o5),
            "k2o": shown(self.k2o),
            "s": shown(self.s),
            "product_form": self.form,
            "density_kg_per_l": shown(self.density_kg_per_l),
            "grade_source": self.source,
        }


def _number(row: dict[str, Any], field: str, where: str) -> Decimal | None:
    value = row[field]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PresetError(f"{where}: {field} must be a number or null")
    return Decimal(str(value))


def _grade(row: dict[str, Any], field: str, where: str) -> Decimal | None:
    value = _number(row, field, where)
    if value is None:
        return None
    if not 0 <= value <= 100:
        raise PresetError(f"{where}: {field} must be between 0 and 100")
    if decimal_places(value) > GRADE_PLACES:
        raise PresetError(f"{where}: {field} has more than {GRADE_PLACES} decimal places")
    return value


def _preset(row: Any, position: int) -> Preset:
    where = f"preset {position}"
    if not isinstance(row, dict):
        raise PresetError(f"{where}: expected a mapping")
    where = f"preset {row.get('slug', position)!s}"
    if row.keys() != FIELDS:
        unknown = sorted(str(key) for key in row.keys() - FIELDS)
        missing = sorted(FIELDS - row.keys())
        raise PresetError(f"{where}: unknown fields {unknown}, missing fields {missing}")
    for field in TEXT_FIELDS:
        if not isinstance(row[field], str) or not row[field].strip():
            raise PresetError(f"{where}: {field} must be non-empty text")
    if KEY.fullmatch(row["slug"]) is None:
        raise PresetError(f"{where}: slug must be lower-case letters, digits and underscores")
    if len(row["name"]) > NAME_MAX:
        raise PresetError(f"{where}: name is longer than {NAME_MAX} characters")
    if len(row["source"]) > SOURCE_MAX:
        raise PresetError(f"{where}: source is longer than {SOURCE_MAX} characters")
    if UNCONFIRMED_SOURCE not in row["source"].lower():
        raise PresetError(f"{where}: source must say {UNCONFIRMED_SOURCE!r}")
    if not row["url"].startswith("https://"):
        raise PresetError(f"{where}: url must start with https://")
    if row["group"] not in GROUPS:
        raise PresetError(f"{where}: unknown group")
    if row["form"] not in FORMS:
        raise PresetError(f"{where}: form must be granular or liquid")

    grades = {field: _grade(row, field, where) for field in GRADE_FIELDS}
    n, p2o5, k2o = grades["n"], grades["p2o5"], grades["k2o"]
    if n is None or p2o5 is None or k2o is None:
        raise PresetError(f"{where}: only s may be null in the grade")
    if sum((value for value in grades.values() if value is not None), Decimal(0)) > 100:
        raise PresetError(f"{where}: the grade adds up to more than 100")

    density = _number(row, "density_kg_per_l", where)
    if density is not None:
        if row["form"] == "granular":
            raise PresetError(f"{where}: a granular type has no density")
        if not 0 < density <= DENSITY_MAX or decimal_places(density) > DENSITY_PLACES:
            raise PresetError(f"{where}: density is out of range")

    return Preset(
        key=row["slug"],
        name=row["name"],
        group=row["group"],
        n=n,
        p2o5=p2o5,
        k2o=k2o,
        s=grades["s"],
        form=row["form"],
        density_kg_per_l=density,
        source=row["source"],
        url=row["url"],
        printed=row["printed"],
        notes=row["notes"],
    )


def parse_presets(rows: Any) -> tuple[Preset, ...]:
    if not isinstance(rows, list) or not rows:
        raise PresetError("the preset file must be a non-empty list")
    presets = tuple(_preset(row, position) for position, row in enumerate(rows, 1))
    keys = [preset.key for preset in presets]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise PresetError(f"duplicate preset keys: {duplicates}")
    return presets


def load_presets(path: Path = PRESETS_PATH) -> tuple[Preset, ...]:
    return parse_presets(yaml.safe_load(path.read_text(encoding="utf-8")))


PRESETS = load_presets()
BY_KEY = {preset.key: preset for preset in PRESETS}


def _matches(preset: Preset, terms: list[str]) -> bool:
    words = f"{preset.name} {preset.group} {preset.form}".casefold().replace("sulf", "sulph")
    for term in terms:
        if term[0].isdigit():
            # A grade is matched from the start of a number: "1-52" must not find 11-52-0.
            if re.search(r"(?<![\d.])" + re.escape(term), f"{preset.grade} {words}") is None:
                return False
        elif term not in words:
            return False
    return True


def search(query: str) -> list[tuple[str, list[Preset]]]:
    """Presets matching every word of the query (name, group, form or grade), by group."""
    cleaned = query[:QUERY_MAX].casefold().replace("sulf", "sulph").replace("%", " ")
    terms = cleaned.split()
    found = [preset for preset in PRESETS if _matches(preset, terms)]
    grouped = ((group, [p for p in found if p.group == group]) for group in GROUPS)
    return [(group, presets) for group, presets in grouped if presets]
