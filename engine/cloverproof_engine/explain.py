"""Plain-language explanations for every number, note and confidence rule.

Text only: no calculation happens here. Every pack constant quoted in a
sentence is tagged PLACEHOLDER (or with its source when validated).
"""

from typing import Literal

from cloverproof_engine.pack import Citation, CitationBasis, ConstantStatus, PackConstant


def num(x: float) -> str:
    return f"{x:,.1f}"


def pct(x: float) -> str:
    return f"{x:.0%}"


def cited(citation: Citation) -> str:
    """Where a value comes from, by basis: only a `stated` value is "read from" a source."""
    if citation.basis is CitationBasis.STATED:
        return f"read from {citation.short()}"
    verb = "derived" if citation.basis is CitationBasis.DERIVED else "inferred"
    return (
        f"{verb} by the engine from {citation.short()}, not a value stated there: "
        f"{(citation.note or '').strip()}"
    )


def tag(c: PackConstant) -> str:
    if c.is_placeholder:
        if c.citation is not None:
            return f"(PLACEHOLDER, not agronomist-validated; {cited(c.citation)})"
        return "(PLACEHOLDER, not agronomist-validated)"
    return f"(source: {c.source})"


# --- nitrogen mass balance ---------------------------------------------------


def crop_n_demand(target_yield: float, uptake: PackConstant, demand: float) -> str:
    return (
        f"Crop N demand = target yield {num(target_yield)} t/ha x "
        f"{num(uptake.value)} kg N per tonne of grain {tag(uptake)} "
        f"= {num(demand)} kg N/ha."
    )


def soil_n_supply(supply: PackConstant) -> str:
    return (
        f"Soil N supply = {num(supply.value)} kg N/ha, a default pack value {tag(supply)}. "
        "Engine v0 does not use measured soil N."
    )


def previous_crop_credit(label: str, credit: PackConstant) -> str:
    return f"N credit from the previous crop ({label}) = {num(credit.value)} kg N/ha {tag(credit)}."


def net_n_requirement(demand: float, soil: float, credit: float, net: float) -> str:
    return (
        f"Net N requirement = crop demand {num(demand)} - soil supply {num(soil)} "
        f"- previous-crop credit {num(credit)} = {num(net)} kg N/ha."
    )


def unbounded_rate(net: float, efficiency: PackConstant, raw: float) -> str:
    return (
        f"Fertilizer N needed = net requirement {num(net)} kg N/ha / fertilizer N "
        f"efficiency {pct(efficiency.value)} {tag(efficiency)} = {num(raw)} kg N/ha."
    )


def n_rate(
    raw: float,
    rate: float,
    bound: Literal["min", "max"] | None,
    min_rate: PackConstant,
    max_rate: PackConstant,
    method_label: str = "nitrogen mass balance",
) -> str:
    base = f"Recommended N rate = {num(rate)} kg N/ha (wheat, {method_label})."
    if bound == "max":
        return (
            f"{base} The calculated {num(raw)} kg N/ha was cut to the pack upper limit "
            f"{num(max_rate.value)} kg N/ha {tag(max_rate)}."
        )
    if bound == "min":
        return (
            f"{base} The calculated {num(raw)} kg N/ha was raised to the pack lower limit "
            f"{num(min_rate.value)} kg N/ha {tag(min_rate)}."
        )
    return (
        f"{base} It is within the pack limits: lower {num(min_rate.value)} kg N/ha "
        f"{tag(min_rate)}, upper {num(max_rate.value)} kg N/ha {tag(max_rate)}."
    )


def n_total(rate: float, area_ha: float, total: float) -> str:
    return f"Total N for the field = {num(rate)} kg N/ha x {num(area_ha)} ha = {num(total)} kg N."


def split_fraction(
    index: int,
    count: int,
    stage_label: str,
    fraction: PackConstant,
    timing: Citation | None = None,
) -> str:
    text = (
        f"Application {index} of {count} ({stage_label}) gets {pct(fraction.value)} "
        f"of the N rate {tag(fraction)}."
    )
    if timing is not None:
        text += f" Timing {cited(timing)} (PLACEHOLDER, not agronomist-validated)."
    return text


def split_rate(index: int, fraction: float, rate: float, split: float) -> str:
    return (
        f"Application {index} rate = {pct(fraction)} x {num(rate)} kg N/ha = {num(split)} kg N/ha."
    )


def split_total(index: int, split: float, area_ha: float, total: float) -> str:
    return (
        f"Application {index} total = {num(split)} kg N/ha x {num(area_ha)} ha = {num(total)} kg N."
    )


def _timing_tag(status: ConstantStatus, citation: Citation | None) -> str:
    label = (
        "PLACEHOLDER, not agronomist-validated"
        if status is ConstantStatus.PLACEHOLDER
        else "validated pack"
    )
    return f"({label}; {cited(citation)})" if citation is not None else f"({label})"


def split_line(
    index: int, count: int, window: str, status: ConstantStatus, citation: Citation | None
) -> str:
    return (
        f"Application {index} of {count} in the pack's split plan. "
        f"Timing window: {window} {_timing_tag(status, citation)}."
    )


def no_split_stage_label() -> str:
    return "Single application (no split defined in the pack; timing not set)"


def no_split_fraction(pack_id: str, version: str, crop: str) -> str:
    return (
        f"No split is defined in pack '{pack_id}' {version} for {crop}: "
        "this one application gets the full N rate."
    )


def no_split_line(pack_id: str, version: str, crop: str) -> str:
    return (
        f"No split is defined in pack '{pack_id}' {version} for {crop}, so the N is one "
        "application. The pack gives no timing window and the engine does not invent one; "
        "the agronomist sets the timing."
    )


# --- nitrogen yield x price-ratio table ---------------------------------------


def table_n_rate(
    target_yield: float,
    ratio: float,
    rate: float,
    cell: PackConstant,
    bracket_yield: tuple[float, float],
    bracket_ratio: tuple[float, float],
    corners: list[float],
    prices: str | None = None,
) -> str:
    where = (
        f"expected yield {num(target_yield)} t/ha and N:grain price ratio {num(ratio)} "
        "(kg grain per kg N)"
    )
    if prices:
        where += f" ({prices})"
    if len(corners) == 1:
        return f"Table N rate = {num(rate)} kg N/ha: the pack table cell at {where} {tag(cell)}."
    return (
        f"Table N rate = {num(rate)} kg N/ha at {where}, interpolated bilinearly between "
        f"yields {num(bracket_yield[0])}-{num(bracket_yield[1])} t/ha and price ratios "
        f"{num(bracket_ratio[0])}-{num(bracket_ratio[1])} (cells "
        f"{', '.join(num(c) for c in corners)} kg N/ha) {tag(cell)}. "
        "Bilinear interpolation is an engine choice, not stated by the table."
    )


def wheat_class_scope(label: str) -> str:
    return f"Scope: {label}."


def assumes_no_manure() -> str:
    return "Assumes no manure applied (input manure_applied = false); no manure N credit is used."


def manure_not_supported() -> str:
    return (
        "the engine has no manure N credit yet, so it gives no N rate when manure was applied; "
        "the agronomist decides N for this field"
    )


def table_rate_after_credit(table_rate: float, credit: float, net: float) -> str:
    return (
        f"Table rate {num(table_rate)} - previous-crop credit {num(credit)} "
        f"= {num(net)} kg N/ha before the pack limits."
    )


# --- notes ---------------------------------------------------------------------


PkTestMissing = Literal["no_test", "estimate", "no_p_or_k_value"]

_PK_TEST_MISSING: dict[str, str] = {
    "no_test": "No soil test",
    "estimate": "The soil test is an estimate, not a lab result",
    "no_p_or_k_value": "The lab soil test has no P or K value",
}


def pk_soil_test_recommended(reason: PkTestMissing) -> str:
    return (
        f"{_PK_TEST_MISSING[reason]}: phosphorus (P) and potassium (K) are not recommended. "
        "Recommend a lab soil test for P and K (record extraction method per nutrient, "
        "depth and date)."
    )


def pk_not_calculated_v0() -> str:
    return (
        "Engine v0 calculates nitrogen only. P and K are not recommended by the engine; "
        "the agronomist decides P and K from the soil test."
    )


def pack_has_placeholders(pack_id: str, version: str) -> str:
    return (
        f"Pack '{pack_id}' {version} contains PLACEHOLDER constants that are not "
        "agronomist-validated. Do not give these numbers to a farmer without review."
    )


def soil_nitrate_not_used(method_id: str = "n_mass_balance") -> str:
    if method_id == "n_yield_price_table":
        return (
            "The soil test includes nitrate-N, but the engine does not use measured soil N; "
            "the N rate comes from the pack's yield x price-ratio table only."
        )
    return (
        "The soil test includes nitrate-N, but engine v0 does not use measured soil N; "
        "the pack default soil N supply was used instead."
    )


# --- confidence rules -------------------------------------------------------------


def c1_no_soil_test() -> str:
    return "No soil test: confidence is at most medium (N only; P and K need a soil test)."


def c2_soil_test_estimated() -> str:
    return "The soil test is an estimate, not a lab result: confidence is at most medium."


def c3_soil_test_stale(age_years: float, limit: PackConstant) -> str:
    return (
        f"The soil test is {num(age_years)} years old, older than {num(limit.value)} years "
        f"{tag(limit)}: confidence is at most medium."
    )


def c4_target_yield_implausible(target: float, low: PackConstant, high: PackConstant) -> str:
    return (
        f"Target yield {num(target)} t/ha is outside the expected range: "
        f"lower {num(low.value)} t/ha {tag(low)}, upper {num(high.value)} t/ha {tag(high)}. "
        "Confidence is low."
    )


def c5_rate_at_bound(bound: Literal["min", "max"]) -> str:
    side = "upper" if bound == "max" else "lower"
    return f"The N rate was limited by the pack {side} limit: confidence is at most medium."


def c6_placeholder_constant_used(pack_id: str, version: str, paths: list[str]) -> str:
    return (
        f"This recommendation uses PLACEHOLDER constants from pack '{pack_id}' {version}: "
        f"{', '.join(paths)}. Confidence is low until the agronomist validates them."
    )
