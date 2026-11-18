"""Product matching: an N line's need -> a catalog product -> a quantity. Pure.

The engine never picks a product on its own. A product must first be safe for an N-only
need (it holds N and adds no P or K: rule 3, and the engine gives no P/K rate yet). The
choice among safe products is agronomy and comes only from the pack's `product_rules`.
Without a rule, or when the rule does not settle it, the line stays nutrient-only and
says why. Nothing here looks at prices or vendors, and matching never touches the N
numbers. Its one effect on confidence is rule C7 in `confidence.py`: a matched product
chosen under a PLACEHOLDER rule caps it at low. A grade, density or area that gives no
finite quantity is a coded non-match on the line, not an error.
"""

from dataclasses import dataclass, field
from typing import Literal

from cloverproof_engine import explain, units
from cloverproof_engine.models import ProductForm, ProductInput, RecommendationInput
from cloverproof_engine.pack import Pack, ProductRules, RuleValue, SulphurRule
from cloverproof_engine.results import (
    ExplainedNumber,
    NutrientResult,
    ProductGrade,
    ProductMatch,
    ProductNotMatched,
    SplitApplication,
    UsedProductRule,
)

Selection = Literal["pack_preference", "single_fit"]


@dataclass(frozen=True)
class _Decision:
    """The outcome for the whole catalog; every line with an N need shares it."""

    rules_used: list[UsedProductRule]
    product: ProductInput | None = None
    selection: Selection | None = None
    code: str | None = None
    fitting: list[str] = field(default_factory=list)
    explanation: str = ""


def match_products(
    inputs: RecommendationInput, pack: Pack, nitrogen: NutrientResult
) -> NutrientResult:
    """The N result with a product outcome on each line; unchanged if no `products`."""
    if inputs.products is None:
        return nitrogen
    decision = _decide(inputs, pack, inputs.products)
    splits = [
        line.model_copy(update={"product_match": _line_outcome(i, line, decision, inputs.area_ha)})
        for i, line in enumerate(nitrogen.splits, 1)
    ]
    return nitrogen.model_copy(update={"splits": splits})


# --- which product ----------------------------------------------------------------


def _unsafe_reason(product: ProductInput) -> str | None:
    """Why a product can never carry an N-only need. Not a pack decision."""
    if product.n_pct == 0:
        return explain.product_has_no_n(product.name)
    if product.p2o5_pct > 0 or product.k2o_pct > 0:
        return explain.product_adds_p_or_k(product.name, product.p2o5_pct, product.k2o_pct)
    return None


def _used(path: str, value: str, rule: RuleValue[object]) -> UsedProductRule:
    return UsedProductRule(
        path=path, value=value, status=rule.status, source=rule.source, citation=rule.citation
    )


def _by_name(products: list[ProductInput]) -> list[ProductInput]:
    return sorted(products, key=lambda p: p.name.casefold())


def _decide(inputs: RecommendationInput, pack: Pack, products: list[ProductInput]) -> _Decision:
    if not products:
        return _Decision(rules_used=[], code="no_products", explanation=explain.no_products())

    safe: list[ProductInput] = []
    excluded: list[str] = []
    for product in _by_name(products):
        reason = _unsafe_reason(product)
        if reason is None:
            safe.append(product)
        else:
            excluded.append(reason)

    rules = pack.crops[inputs.crop].product_rules
    if rules is None:
        if not safe:
            return _Decision(
                rules_used=[], code="none_fit", explanation=explain.no_product_fits(excluded)
            )
        return _Decision(
            rules_used=[],
            code="no_choice_rule",
            fitting=[p.name for p in safe],
            explanation=explain.no_choice_rule(
                pack.id, pack.version, [_listed(p) for p in safe], excluded
            ),
        )
    return _apply_rules(f"crops.{inputs.crop.value}.product_rules", rules, safe, excluded)


def _listed(product: ProductInput) -> str:
    return explain.product_listing(product.name, product.s_pct)


def _apply_rules(
    base: str, rules: ProductRules, safe: list[ProductInput], excluded: list[str]
) -> _Decision:
    forms = rules.allowed_forms
    sulphur = rules.sulphur
    used = [
        _used(f"{base}.allowed_forms", ", ".join(f.value for f in forms.value), forms),
        _used(f"{base}.sulphur", sulphur.value.value, sulphur),
    ]
    excluded = list(excluded)
    fitting: list[ProductInput] = []
    for product in safe:
        if product.form not in forms.value:
            excluded.append(explain.product_form_excluded(product.name, product.form, forms))
        elif product.s_pct > 0 and sulphur.value is SulphurRule.EXCLUDE:
            excluded.append(explain.product_sulphur_excluded(product.name, product.s_pct, sulphur))
        else:
            fitting.append(product)
    if not fitting:
        return _Decision(
            rules_used=used, code="none_fit", explanation=explain.no_product_fits(excluded)
        )

    preference = rules.preference
    used.append(_used(f"{base}.preference", "; ".join(preference.value), preference))
    by_key = {p.name.casefold(): p for p in fitting}
    for name in preference.value:
        chosen = by_key.get(name.casefold())
        if chosen is not None:
            return _Decision(
                rules_used=used,
                product=chosen,
                selection="pack_preference",
                explanation=explain.product_selected_by_preference(preference),
            )

    names = [p.name for p in fitting]
    listed = [_listed(p) for p in fitting]
    if len(fitting) > 1:
        return _Decision(
            rules_used=used,
            code="several_fit",
            fitting=names,
            explanation=explain.several_products_fit(listed, preference),
        )
    single = rules.allow_single_fit
    used.append(_used(f"{base}.allow_single_fit", str(single.value).lower(), single))
    if single.value:
        return _Decision(
            rules_used=used,
            product=fitting[0],
            selection="single_fit",
            explanation=explain.product_selected_as_single_fit(single),
        )
    return _Decision(
        rules_used=used,
        code="single_fit_not_allowed",
        fitting=names,
        explanation=explain.single_fit_not_allowed(listed[0], single),
    )


# --- how much, per line -----------------------------------------------------------


def _line_outcome(
    index: int, line: SplitApplication, decision: _Decision, area_ha: float
) -> ProductMatch | ProductNotMatched:
    product = decision.product
    if line.rate.value == 0:
        return ProductNotMatched(
            code="no_n_needed",
            fitting_products=[],
            rules_used=[],
            explanation=explain.no_n_needed(index),
        )
    if product is None or decision.selection is None:
        return ProductNotMatched.model_validate(
            {
                "code": decision.code,
                "fitting_products": decision.fitting,
                "rules_used": decision.rules_used,
                "explanation": decision.explanation,
            }
        )
    try:
        return _matched_line(index, line, product, decision, area_ha)
    except units.NonFiniteQuantityError:
        return ProductNotMatched(
            code="quantity_out_of_range",
            fitting_products=[],
            rules_used=decision.rules_used,
            explanation=explain.product_quantity_out_of_range(index, product.name),
        )


def _grade_number(name: str, value: float, unit: str, product: ProductInput) -> ExplainedNumber:
    return ExplainedNumber(
        name=f"product_grade_{name}",
        value=value,
        unit=unit,
        explanation=explain.product_grade(product.name, value, unit, product.grade_source),
        uses_placeholder=False,
    )


def _matched_line(
    index: int,
    line: SplitApplication,
    product: ProductInput,
    decision: _Decision,
    area_ha: float,
) -> ProductMatch:
    need = line.rate.value
    rate = units.nutrient_to_product_kg(need, product.n_pct)
    total = units.finite_quantity(rate * area_ha, "product total")
    # A quantity is only as settled as the N rate and the rules that chose the product.
    placeholder = line.rate.uses_placeholder or any(
        rule.status == "PLACEHOLDER" for rule in decision.rules_used
    )

    volume_rate = None
    if product.form is ProductForm.LIQUID and product.density_kg_per_l is not None:
        litres = units.kg_to_litres(rate, product.density_kg_per_l)
        volume_rate = ExplainedNumber(
            name=f"split_{index}_product_volume_rate",
            value=litres,
            unit="L product/ha",
            explanation=explain.product_volume_rate(
                index, rate, product.density_kg_per_l, litres, product.grade_source
            ),
            uses_placeholder=placeholder,
        )

    sulphur_rate = None
    if product.s_pct > 0:
        sulphur = units.product_kg_to_nutrient(rate, product.s_pct)
        sulphur_rate = ExplainedNumber(
            name=f"split_{index}_product_sulphur_rate",
            value=sulphur,
            unit="kg S/ha",
            explanation=explain.product_sulphur_rate(index, rate, product.s_pct, sulphur),
            uses_placeholder=placeholder,
        )

    selection = decision.selection
    if selection is None:
        raise ValueError("a matched line needs a selection")
    return ProductMatch(
        product_id=product.id,
        product_name=product.name,
        form=product.form,
        grade=ProductGrade(
            n=_grade_number("n", product.n_pct, "% N", product),
            p2o5=_grade_number("p2o5", product.p2o5_pct, "% P2O5", product),
            k2o=_grade_number("k2o", product.k2o_pct, "% K2O", product),
            s=_grade_number("s", product.s_pct, "% S", product),
        ),
        grade_source=product.grade_source,
        selection=selection,
        rate=ExplainedNumber(
            name=f"split_{index}_product_rate",
            value=rate,
            unit="kg product/ha",
            explanation=explain.product_rate(index, need, product.n_pct, rate),
            uses_placeholder=placeholder,
        ),
        total=ExplainedNumber(
            name=f"split_{index}_product_total",
            value=total,
            unit="kg product",
            explanation=explain.product_total(index, rate, area_ha, total),
            uses_placeholder=placeholder,
        ),
        volume_rate=volume_rate,
        sulphur_rate=sulphur_rate,
        rules_used=decision.rules_used,
        explanation=explain.product_match_line(
            product.name, decision.explanation, product.s_pct, decision.rules_used
        ),
    )
