"""What the plan page, the diff and the proof say about one N line's timing and product.

Reads the stored engine document and calculates nothing. Documents from engine 0.2/0.3
have no `timing_window`, `explanation` or `product_match` keys and keep today's display.
A document has no `product_match` when the engine ran without `products`.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any

from cloverproof_engine import explain

NO_TIMING_SET = "No timing set: the pack has no split plan"
NO_PRODUCT_YET = "No product matched yet"  # the document has no product outcome at all
NO_PRODUCT_MATCHED = "No product matched"
PRODUCT_WITHDRAWN = "Any product outcome withdrawn: the N rate was edited"
PLACEHOLDER_RULE = "Selected by a PLACEHOLDER pack rule, not validated"
UNCHOSEN_PRODUCTS = "Products the pack rules did not choose between"
PROOF_TIMING_NOTE = (
    "Timing is the growth-stage text from the country pack (no weather-based window in this"
    " version)."
)
PROOF_NO_TIMING_NOTE = (
    "No timing is set where the pack has no split plan (no weather-based window in this version)."
)

PLACEHOLDER = "PLACEHOLDER"

# Engine sentences that assume an agronomist reviewed the line. Only a proof approved by
# one may say them (CLAUDE.md rules 8 and 11); other proofs state what is still needed.
_AGRONOMIST_PHRASES = (
    ("the agronomist confirms", "an agronomist must confirm"),
    ("the agronomist chooses", "an agronomist must choose"),
    ("The agronomist sets the product", "An agronomist must set the product"),
)

# Stored edited numbers (before the wording became "reviewer") name an agronomist, though a
# superadmin can edit too. Prefix only: the free-text reason after it stays as written.
_EDIT_PREFIXES = (
    ("Set by agronomist:", "Set by reviewer:"),
    ("Rescaled from the agronomist's N rate", "Rescaled from the reviewer's N rate"),
    ("Rescaled to the agronomist's N rate", "Rescaled to the reviewer's N rate"),
)


def share_text(fraction: float) -> str:
    """A share as the engine writes it in its explanations: 12.5%, 40%."""
    return explain.pct(float(fraction))


def is_old_line(split: Mapping[str, Any]) -> bool:
    """Stored before engine 0.4: shown as it always was, with whole-percent shares."""
    return "timing_window" not in split


def has_line_detail(split: Mapping[str, Any]) -> bool:
    return not is_old_line(split) or bool(split.get("explanation") or outcome(split))


def outcome(split: Mapping[str, Any]) -> Mapping[str, Any] | None:
    match: Mapping[str, Any] | None = split.get("product_match")
    return match or None


def _placeholder_rules(match: Mapping[str, Any]) -> bool:
    return any(rule.get("status") == PLACEHOLDER for rule in match.get("rules_used", []))


def selected_by_placeholder_rule(match: Mapping[str, Any]) -> bool:
    return bool(match.get("matched")) and _placeholder_rules(match)


def not_matched_title(match: Mapping[str, Any]) -> str:
    return PRODUCT_WITHDRAWN if match.get("code") == "rate_edited" else NO_PRODUCT_MATCHED


def product_numbers(split: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Every product number the plan page and the proof show for this line."""
    match = outcome(split)
    if match is None or not match.get("matched"):
        return
    yield from match["grade"].values()
    yield match["rate"]
    for key in ("volume_rate", "sulphur_rate"):
        if match.get(key):
            yield match[key]


def has_placeholder(splits: Iterable[Mapping[str, Any]]) -> bool:
    """A line's timing window, product rule or product number is PLACEHOLDER."""
    for split in splits:
        if (split.get("timing_window") or {}).get("status") == PLACEHOLDER:
            return True
        match = outcome(split)
        if match is not None and _placeholder_rules(match):
            return True
        if any(number.get("uses_placeholder") for number in product_numbers(split)):
            return True
    return False


def product_label(split: Mapping[str, Any]) -> str:
    """The product attribute of the engine-vs-final diff."""
    match = outcome(split)
    if match is None:
        return NO_PRODUCT_YET
    return str(match["product_name"]) if match.get("matched") else NO_PRODUCT_MATCHED


def timing_label(split: Mapping[str, Any]) -> str:
    """The timing attribute of the engine-vs-final diff. The pack gives no dates."""
    if is_old_line(split):
        return f"{split.get('stage_label', 'Stage not set')} (no dates yet)"
    window = split["timing_window"]
    if window is None:
        return NO_TIMING_SET
    status = ", PLACEHOLDER" if window.get("status") == PLACEHOLDER else ""
    return f"{window['label']}{status} (no dates yet)"


def proof_timing_note(splits: Sequence[Mapping[str, Any]]) -> str:
    """The sentence above the proof's split table; true for a line with no timing."""
    no_window = any(not is_old_line(s) and s["timing_window"] is None for s in splits)
    return PROOF_NO_TIMING_NOTE if no_window else PROOF_TIMING_NOTE


def neutral_edit_text(text: str) -> str:
    for stored, neutral in _EDIT_PREFIXES:
        if text.startswith(stored):
            return neutral + text[len(stored) :]
    return text


def without_agronomist_claim(text: str) -> str:
    for engine_words, neutral in _AGRONOMIST_PHRASES:
        text = text.replace(engine_words, neutral)
    return text
