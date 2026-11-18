"""Plain-language explanations for every number, note and confidence rule.

Text only: the one calculation here decides whether a rounding note is needed. Every
pack constant quoted in a sentence is tagged PLACEHOLDER (or with its source when validated).
"""

from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from cloverproof_engine.models import ProductForm
from cloverproof_engine.pack import (
    Citation,
    CitationBasis,
    ConstantStatus,
    PackConstant,
    PkCaution,
    RuleValue,
)

if TYPE_CHECKING:
    from cloverproof_engine.results import UsedProductRule


def num(x: float) -> str:
    return f"{x:,.1f}"


def pct(x: float) -> str:
    """A percentage with one decimal, dropped when it is zero: 12.5%, 40%."""
    return f"{x:.1%}".replace(".0%", "%")


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


def rounded_for_display() -> str:
    return (
        " These lines do not add up exactly as shown: rounded for display; stored values are exact."
    )


def rounding_note(
    values: list[float], shown: Callable[[float], str], whole: float | None = None
) -> str:
    """The rounding sentence when the lines, as displayed, do not add up to the whole.

    `whole` is the figure shown for all lines together; by default their exact sum.
    """
    target = sum(values) if whole is None else whole

    def displayed(value: float) -> Decimal:
        return Decimal(shown(value).replace(",", "").removesuffix("%"))

    adds_up = sum(displayed(v) for v in values) == displayed(target)
    return "" if adds_up else rounded_for_display()


def no_split_rate(rate: float) -> str:
    return f"Full N rate on this line = {num(rate)} kg N/ha."


def no_split_total(rate: float, area_ha: float, total: float) -> str:
    return f"Total on this line = {num(rate)} kg N/ha x {num(area_ha)} ha = {num(total)} kg N."


def _timing_tag(citation: Citation | None) -> str:
    label = "PLACEHOLDER, not agronomist-validated"
    return f"({label}; {cited(citation)})" if citation is not None else f"({label})"


def split_line(index: int, count: int, window: str, citation: Citation | None) -> str:
    return (
        f"Application {index} of {count} in the pack's split plan. "
        f"Pack timing wording: {window} {_timing_tag(citation)}."
    )


def no_split_stage_label() -> str:
    return "Full N rate, not split (no split plan in the pack; timing not set)"


def no_split_fraction(pack_id: str, version: str, crop: str) -> str:
    return (
        f"No split is defined in pack '{pack_id}' {version} for {crop}: "
        "this line carries the full N rate."
    )


def no_split_line(pack_id: str, version: str, crop: str) -> str:
    return (
        f"Pack '{pack_id}' {version} defines no split plan for {crop}, so the engine shows the "
        "N rate as one line. This is not advice to apply it in one pass. The pack gives no "
        "timing window and the engine does not invent one."
    )


# --- product matching ----------------------------------------------------------


def grade_pct(x: float) -> str:
    return f"{x:g} %"


def operand(x: float) -> str:
    """A number a sum is worked from, precise enough to redo the sum by hand."""
    return f"{x:g}"


def _rule_tag(status: ConstantStatus, source: str | None, citation: Citation | None = None) -> str:
    where = f"; {cited(citation)}" if citation is not None else ""
    if status is ConstantStatus.PLACEHOLDER:
        return f"(PLACEHOLDER, not agronomist-validated{where})"
    return f"(source: {source}{where})"


def _pack_rule(rule: RuleValue[Any]) -> str:
    return _rule_tag(rule.status, rule.source, rule.citation)


def _excluded_sentence(excluded: list[str]) -> str:
    return f" Not usable: {'; '.join(excluded)}." if excluded else ""


def product_has_no_n(name: str) -> str:
    return f"{name} contains no N"


def product_adds_p_or_k(name: str, p2o5_pct: float, k2o_pct: float) -> str:
    return (
        f"{name} would add P or K ({grade_pct(p2o5_pct)} P2O5, {grade_pct(k2o_pct)} K2O), and "
        "an N line takes only products without P or K"
    )


def product_form_excluded(name: str, form: ProductForm, rule: RuleValue[Any]) -> str:
    return f"{name} is {form.value}, a form the pack does not allow {_pack_rule(rule)}"


def product_sulphur_excluded(name: str, s_pct: float, rule: RuleValue[Any]) -> str:
    return f"{name} contains {grade_pct(s_pct)} sulphur, which the pack excludes {_pack_rule(rule)}"


def product_listing(name: str, s_pct: float) -> str:
    return f"{name} (contains {grade_pct(s_pct)} sulphur)" if s_pct > 0 else name


def no_products() -> str:
    return "No catalog products were given, so this line stays nutrient-only."


def no_n_needed(index: int) -> str:
    return f"Application {index} needs no N, so no product is named."


def product_rate_edited(index: int) -> str:
    return (
        f"The N rate of application {index} was edited after matching, so any product outcome "
        "from the engine no longer applies and is withdrawn. The agronomist sets the product."
    )


def product_quantity_out_of_range(index: int, name: str) -> str:
    return (
        f"No usable quantity of {name} can be computed for application {index}: its label "
        "grade or density, or the field area, gives a number too large or too small to "
        "calculate. Check the catalog entry. This line stays nutrient-only; the agronomist "
        "chooses."
    )


def no_product_fits(excluded: list[str]) -> str:
    return (
        "No catalog product fits this N-only need, so this line stays nutrient-only."
        f"{_excluded_sentence(excluded)}"
    )


def no_choice_rule(pack_id: str, version: str, listed: list[str], excluded: list[str]) -> str:
    return (
        f"Pack '{pack_id}' {version} has no product rule, so the engine selects no product "
        f"and this line stays nutrient-only. Products without P or K: {', '.join(listed)}; "
        "the agronomist chooses."
        f"{_excluded_sentence(excluded)}"
    )


def several_products_fit(listed: list[str], preference: RuleValue[Any]) -> str:
    return (
        f"Several products fit: {', '.join(listed)}. The pack preference "
        f"{_pack_rule(preference)} names none of them, so the engine selects none and this "
        "line stays nutrient-only; the agronomist chooses."
    )


def single_fit_not_allowed(listed: str, rule: RuleValue[Any]) -> str:
    return (
        f"Only {listed} fits, but the pack does not allow selecting a product just because "
        f"it is the only fit {_pack_rule(rule)}. This line stays nutrient-only; the "
        "agronomist chooses."
    )


def product_selected_by_preference(rule: RuleValue[Any]) -> str:
    return f"Selected by the pack preference order {_pack_rule(rule)}."


def product_selected_as_single_fit(rule: RuleValue[Any]) -> str:
    return f"Selected as the only fitting product, which the pack allows {_pack_rule(rule)}."


def product_match_line(
    name: str, selection: str, s_pct: float, rules: "Sequence[UsedProductRule]"
) -> str:
    sulphur = (
        f"It also contains {grade_pct(s_pct)} sulphur, which the pack allows; the engine gives "
        "no sulphur recommendation, so this sulphur is not checked against any need."
        if s_pct > 0
        else "It contains no sulphur."
    )
    labels = "; ".join(f"{r.path} {_rule_tag(r.status, r.source, r.citation)}" for r in rules)
    return (
        f"{name} carries this line's N. {selection} It adds no P or K. {sulphur} "
        f"Rules used: {labels}. The engine does not judge whether this product suits the "
        "application timing or adjust for N losses; the agronomist confirms."
    )


def product_grade(name: str, value: float, unit: str, grade_source: str) -> str:
    return f"Label grade of {name}: {value:g} {unit} (source: {grade_source})."


def product_rate(index: int, need: float, n_pct: float, rate: float) -> str:
    return (
        f"Application {index} product rate = {operand(need)} kg N/ha / {grade_pct(n_pct)} N "
        f"= {num(rate)} kg product/ha."
    )


def product_total(index: int, rate: float, area_ha: float, total: float) -> str:
    return (
        f"Application {index} product total = {operand(rate)} kg product/ha x "
        f"{operand(area_ha)} ha "
        f"= {num(total)} kg product."
    )


def product_volume_rate(
    index: int, rate: float, density: float, litres: float, grade_source: str
) -> str:
    return (
        f"Application {index} product volume = {operand(rate)} kg product/ha / "
        f"{operand(density)} kg/L "
        f"(source: {grade_source}) = {num(litres)} L product/ha."
    )


def product_sulphur_rate(index: int, rate: float, s_pct: float, sulphur: float) -> str:
    return (
        f"Sulphur brought by application {index} = {operand(rate)} kg product/ha x "
        f"{grade_pct(s_pct)} S = {num(sulphur)} kg S/ha. A side effect of the product, not a "
        "sulphur recommendation."
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


_SOIL_ESTIMATE_LABEL: dict[str, str] = {
    "phh2o": "Soil pH in water",
    "soc": "Soil organic carbon",
    "nitrogen": "Total soil nitrogen",
    "clay": "Clay content",
    "sand": "Sand content",
    "silt": "Silt content",
}


def soil_estimate_name(prop: str) -> str:
    return f"{_SOIL_ESTIMATE_LABEL[prop]} (estimate)"


def soil_estimate_lower_name(prop: str) -> str:
    return f"{_SOIL_ESTIMATE_LABEL[prop]}, lower end of modelled range (Q0.05)"


def soil_estimate_upper_name(prop: str) -> str:
    return f"{_SOIL_ESTIMATE_LABEL[prop]}, upper end of modelled range (Q0.95)"


def soil_estimate_uncertainty_name(prop: str) -> str:
    return f"{_SOIL_ESTIMATE_LABEL[prop]}, uncertainty ratio"


def soil_estimate_value(
    prop: str,
    depth: str,
    value: float,
    unit: str,
    source: str,
    version: str,
    resolution_m: float,
    retrieved_on: date,
) -> str:
    text = (
        f"{_SOIL_ESTIMATE_LABEL[prop]} at {depth}: {value:g} {unit}. This is a modelled "
        f"estimate from {source} {version} ({resolution_m:g} m grid, retrieved "
        f"{retrieved_on.isoformat()}), not a lab measurement. Confidence: low. It did not "
        "change the N rate."
    )
    if prop == "nitrogen":
        text += " This is total nitrogen, not nitrate (NO3-N), and is not used as soil nitrate."
    return text


def soil_estimate_range(prop: str, depth: str, quantile: str) -> str:
    return (
        f"{quantile} of the modelled {_SOIL_ESTIMATE_LABEL[prop].lower()} at {depth}. Part of "
        "the estimate's stated range, not a lab measurement. It did not change the N rate."
    )


def soil_estimate_uncertainty(prop: str, depth: str) -> str:
    return (
        f"Width of the modelled range for {_SOIL_ESTIMATE_LABEL[prop].lower()} at {depth}: "
        "(Q0.95 - Q0.05) / Q0.50, as published by the source. Higher means less certain. It "
        "did not change the N rate."
    )


def soil_estimate_context(source: str, version: str, lab_test_given: bool) -> str:
    opening = f"These values are a modelled estimate from {source} {version}, not a lab soil test."
    role = (
        "A lab soil test was given and it decides this plan; the estimate is context only."
        if lab_test_given
        else "They are context only and do not count as a soil test."
    )
    return (
        f"{opening} {role} Their confidence is low. They did not change the N rate or the "
        "confidence of this plan. They hold no phosphorus (P) or potassium (K) value, and P "
        "and K rates need a lab soil test."
    )


def pk_not_calculated_v0() -> str:
    return (
        "Engine v0 calculates nitrogen only. P and K are not recommended by the engine; "
        "the agronomist decides P and K from the soil test."
    )


def _with_reasons(text: str, reasons: Sequence[str]) -> str:
    return " ".join([text, *reasons])


def pk_from_lab_test(refusals: Sequence[str]) -> str:
    """Quotes no rate: this text stays true when a reviewer changes the plan's numbers."""
    return _with_reasons(
        "This plan covers nitrogen only: it has no P or K rate. The engine checked the lab "
        "soil test against the pack's P and K tables, but those results are unreviewed, are "
        "not shown and are not part of this plan; the agronomist decides P and K from the "
        "soil test.",
        refusals,
    )


def pk_lab_test_no_rate(refusals: Sequence[str]) -> str:
    return _with_reasons(
        "This plan covers nitrogen only: it has no P or K rate. No value from this lab soil "
        "test could be checked against the pack's P and K tables; the agronomist decides P "
        "and K from the soil test.",
        refusals,
    )


_PK_NAME = {"P": "Phosphorus (P)", "K": "Potassium (K)"}


def _pk_no_rate(nutrient: str) -> str:
    """Says nothing about the other nutrient: no P or K rate is shown in a plan."""
    return f"{_PK_NAME[nutrient]} was not checked against a pack table:"


def _methods(methods: Sequence[str]) -> str:
    return ", ".join(methods)


def pk_no_lab_test(nutrient: str) -> str:
    return f"{_pk_no_rate(nutrient)} a lab soil test is required; there is none."


def pk_no_pack_guidance(nutrient: str, pack_id: str, version: str) -> str:
    return f"{_pk_no_rate(nutrient)} pack '{pack_id}' {version} has no table for this nutrient."


def pk_no_soil_test_value(nutrient: str) -> str:
    return f"{_pk_no_rate(nutrient)} the lab soil test has no value for this nutrient."


def pk_no_method(nutrient: str, available: Sequence[str]) -> str:
    return (
        f"{_pk_no_rate(nutrient)} the soil-test value has no extraction method, so the engine "
        f"cannot tell which table applies. The pack has a table for: {_methods(available)}. "
        "Get the method from the lab report."
    )


def pk_no_table_for_method(
    nutrient: str, method: str, detail: str | None, available: Sequence[str]
) -> str:
    named = f"{method} ({detail.strip()})" if detail and detail.strip() else method
    return (
        f"{_pk_no_rate(nutrient)} the soil-test value was extracted by {named}, and the pack has "
        f"no table for that method. It has a table for: {_methods(available)}. Results from "
        "one extraction method are not read from another method's table."
    )


def pk_sample_depth_mismatch(
    nutrient: str, top_cm: float, bottom_cm: float, depth: PackConstant
) -> str:
    return (
        f"{_pk_no_rate(nutrient)} the sample was taken at {operand(top_cm)}-{operand(bottom_cm)} "
        f"cm, and the pack's table is read for a sample from the surface to "
        f"{operand(depth.value)} cm {tag(depth)}. Refusing another depth is an engine choice."
    )


def pk_outside_table(nutrient: str, level: float, first: str, last: str) -> str:
    return (
        f"{_pk_no_rate(nutrient)} the soil-test level {num(level)} is outside the pack table "
        f"(bands {first} to {last}). The engine does not extrapolate (engine choice)."
    )


def pk_soil_test_value(
    form: str,
    amount: float,
    reported_form: str,
    reported: float,
    reported_unit: str,
    table_label: str,
    sample_date: str,
) -> str:
    where = f"lab soil test of {sample_date}, {table_label}"
    if form == reported_form:
        return f"Soil test = {operand(amount)} mg {form}/kg, as reported ({where})."
    return (
        f"Soil test = {operand(amount)} mg {form}/kg, converted from the reported "
        f"{operand(reported)} {reported_unit} {reported_form} by atomic weights ({where})."
    )


def pk_table_rate(
    form: str,
    rate: float,
    table_label: str,
    band: str,
    response: str,
    response_label: str,
    cell: PackConstant,
    assumes: str,
    caution: PkCaution | None,
) -> str:
    """The rate and the response rating are separate facts: neither is worded as the other."""
    parts = [
        f"Table rate = {num(rate)} kg {form}/ha: pack table for the {table_label}, band "
        f"{band} {tag(cell)}. Assumes {assumes}. The band is the last one whose lower limit "
        "the soil-test level reaches, with no interpolation between bands (engine choice, "
        "not stated by the table).",
        f"Response rating for this band, separate from the rate: {response_label} ({response}).",
    ]
    if rate == 0:
        parts.append("A rate of 0 is the table's entry for this band, not a response rating.")
    if caution is not None:
        parts.append(f"Caution printed with the table: {caution.text} ({cited(caution.citation)}).")
    return " ".join(parts)


def pk_converted_rate(
    form: str, amount: float, table_form: str, table_rate: float, assumes: str
) -> str:
    return (
        f"The same rate as the element or oxide: {num(table_rate)} kg {table_form}/ha "
        f"= {operand(amount)} kg {form}/ha, by atomic weights. Assumes {assumes}."
    )


def pk_total(form: str, rate: float, area_ha: float, total: float, assumes: str) -> str:
    return (
        f"Total for the field = {operand(rate)} kg {form}/ha x {operand(area_ha)} ha "
        f"= {num(total)} kg {form}. Assumes {assumes}."
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
        f"This recommendation uses PLACEHOLDER constants or timing windows from pack "
        f"'{pack_id}' {version}: {', '.join(paths)}. "
        "Confidence is low until a human agronomist validates them."
    )


def c8_pk_placeholder_not_in_plan(pack_id: str, version: str, paths: list[str]) -> str:
    return (
        f"The P and K table check used PLACEHOLDER constants from pack '{pack_id}' {version}: "
        f"{', '.join(paths)}. Those P and K results are not part of this plan; this rule "
        "still keeps confidence low until a human agronomist validates the constants."
    )


def c7_placeholder_product_rule_used(pack_id: str, version: str, paths: list[str]) -> str:
    return (
        f"The engine's product choice relied on PLACEHOLDER rules from pack '{pack_id}' "
        f"{version}: {', '.join(paths)}. "
        "Confidence is low until a human agronomist validates them."
    )


def c6_timing_window_missing(pack_id: str, version: str) -> str:
    return f"Pack '{pack_id}' {version} gives no timing window for this N: confidence is low."
