"""Plain-language explanations for every number, note and confidence rule.

Text only: no calculation happens here. Every pack constant quoted in a
sentence is tagged PLACEHOLDER (or with its source when validated).
"""

from typing import Literal

from cloverproof_engine.pack import PackConstant


def num(x: float) -> str:
    return f"{x:,.1f}"


def pct(x: float) -> str:
    return f"{x:.0%}"


def tag(c: PackConstant) -> str:
    if c.is_placeholder:
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
) -> str:
    base = f"Recommended N rate = {num(rate)} kg N/ha (wheat, nitrogen mass balance)."
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
        f"{base} It is within the pack limits {num(min_rate.value)}-{num(max_rate.value)} "
        f"kg N/ha {tag(max_rate)}."
    )


def n_total(rate: float, area_ha: float, total: float) -> str:
    return f"Total N for the field = {num(rate)} kg N/ha x {num(area_ha)} ha = {num(total)} kg N."


def split_fraction(index: int, count: int, stage_label: str, fraction: PackConstant) -> str:
    return (
        f"Application {index} of {count} ({stage_label}) gets {pct(fraction.value)} "
        f"of the N rate {tag(fraction)}."
    )


def split_rate(index: int, fraction: float, rate: float, split: float) -> str:
    return (
        f"Application {index} rate = {pct(fraction)} x {num(rate)} kg N/ha = {num(split)} kg N/ha."
    )


def split_total(index: int, split: float, area_ha: float, total: float) -> str:
    return (
        f"Application {index} total = {num(split)} kg N/ha x {num(area_ha)} ha = {num(total)} kg N."
    )


# --- notes ---------------------------------------------------------------------


def pk_soil_test_recommended() -> str:
    return (
        "No soil test: phosphorus (P) and potassium (K) are not recommended. "
        "Recommend a soil test for P and K (record extraction method, depth and date)."
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


def soil_nitrate_not_used() -> str:
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
        f"Target yield {num(target)} t/ha is outside the expected range "
        f"{num(low.value)}-{num(high.value)} t/ha {tag(low)}: confidence is low."
    )


def c5_rate_at_bound(bound: Literal["min", "max"]) -> str:
    side = "upper" if bound == "max" else "lower"
    return f"The N rate was limited by the pack {side} limit: confidence is at most medium."


def c6_pack_has_placeholders(pack_id: str, version: str) -> str:
    return (
        f"Pack '{pack_id}' {version} uses PLACEHOLDER constants: confidence is low "
        "until the agronomist validates them."
    )
