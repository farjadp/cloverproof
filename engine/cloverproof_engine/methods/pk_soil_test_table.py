"""P and K from a lab soil test (method id `pk_soil_test_table`).

For guidance published as tables of rate by soil-test band, valid for one extraction
method each (e.g. Ontario Publication 811, Tables 4-20 and 4-21; pack ca-on).

    soil-test level = the lab value, in the table's `soil_test_form` (through `units.py`)
    rate            = the rate of the band that level falls in, in the pack table
                      for that value's own extraction method
    total           = rate x area

Each nutrient either gets a rate or is refused with a plain reason. There is no
fallback: a value is never read from a table for another method. Refused: no lab test,
no pack guidance, no value, no method, no table for the method, a sampling depth other
than the pack's, a level outside the table.

Engine choices, not from a source (TODO(agronomist)): a level between two printed bands
takes the lower band; no interpolation between bands; a level outside the table is
refused; a test from another depth is refused.
"""

import math
from typing import ClassVar, Literal

from cloverproof_engine import explain, units
from cloverproof_engine.methods._shared import any_placeholder
from cloverproof_engine.methods.base import NutrientMethod
from cloverproof_engine.models import (
    NutrientForm,
    RecommendationInput,
    SoilTest,
    SoilTestSource,
    SoilTestValue,
)
from cloverproof_engine.pack import Pack, PhosphorusPotassiumConfig, PkRateTable
from cloverproof_engine.results import (
    ExplainedNumber,
    FormAmount,
    PkRecommended,
    PkRefused,
    PkResults,
    UsedConstant,
)

Nutrient = Literal["P", "K"]


def _band_index(table: PkRateTable, level: float) -> int | None:
    """The last band whose lower limit `level` reaches, if `level` is within the table.

    The closeness check keeps a value on a band edge in that band after a form
    conversion (P 10 -> P2O5 -> P can come back a hair below 10).
    """

    def reaches(limit: float) -> bool:
        return level >= limit or math.isclose(level, limit)

    found = None
    for i, band in enumerate(table.bands):
        if reaches(band.low):
            found = i
    if found is None:
        return None
    high = table.bands[found].high
    is_last = found == len(table.bands) - 1
    if is_last and high is not None and level > high and not math.isclose(level, high):
        return None
    return found


class PkSoilTestTable(NutrientMethod[PkResults]):
    method_id: ClassVar[str] = "pk_soil_test_table"
    nutrient: ClassVar[str] = "PK"

    def calculate(self, inputs: RecommendationInput, pack: Pack) -> PkResults:
        cfg = pack.crops[inputs.crop].phosphorus_potassium
        if cfg is None:
            raise ValueError(f"pack {pack.id} {pack.version} has no P/K tables")
        return PkResults(
            phosphorus=self._line("P", inputs, pack, cfg),
            potassium=self._line("K", inputs, pack, cfg),
        )

    def _line(
        self,
        nutrient: Nutrient,
        inputs: RecommendationInput,
        pack: Pack,
        cfg: PhosphorusPotassiumConfig,
    ) -> PkRecommended | PkRefused:
        def refuse(code: str, explanation: str) -> PkRefused:
            return PkRefused.model_validate(
                {"nutrient": nutrient, "code": code, "explanation": explanation}
            )

        soil = inputs.soil_test
        if soil is None or soil.source is not SoilTestSource.LAB:
            return refuse("no_lab_test", explain.pk_no_lab_test(nutrient))
        nutrient_cfg = cfg.nutrients.get(nutrient)
        if nutrient_cfg is None:
            return refuse(
                "no_pack_guidance", explain.pk_no_pack_guidance(nutrient, pack.id, pack.version)
            )
        value = soil.value_for(nutrient)
        if value is None:
            return refuse("no_soil_test_value", explain.pk_no_soil_test_value(nutrient))
        available = [method.value for method in nutrient_cfg.tables]
        method = value.extraction_method
        if method is None:
            return refuse("no_extraction_method", explain.pk_no_method(nutrient, available))
        table = nutrient_cfg.tables.get(method)
        if table is None:
            return refuse(
                "no_table_for_method",
                explain.pk_no_table_for_method(
                    nutrient, method.value, value.extraction_method_detail, available
                ),
            )
        depth = cfg.sample_depth_cm
        if soil.depth_top_cm != 0 or soil.depth_bottom_cm != depth.value:
            return refuse(
                "sample_depth_mismatch",
                explain.pk_sample_depth_mismatch(
                    nutrient, soil.depth_top_cm, soil.depth_bottom_cm, depth
                ),
            )

        elemental_form = units.elemental_form(nutrient)
        oxide_form = units.oxide_form(nutrient)
        level = units.convert_form(value.value_mg_per_kg, value.form, table.soil_test_form)
        index = _band_index(table, level)
        if index is None:
            return refuse(
                "outside_table",
                explain.pk_outside_table(
                    nutrient,
                    level,
                    table.band_label(table.bands[0]),
                    table.band_label(table.bands[-1]),
                ),
            )
        return self._recommended(
            nutrient, inputs, soil, value, table, index, cfg, elemental_form, oxide_form
        )

    def _recommended(
        self,
        nutrient: Nutrient,
        inputs: RecommendationInput,
        soil: SoilTest,
        value: SoilTestValue,
        table: PkRateTable,
        index: int,
        cfg: PhosphorusPotassiumConfig,
        elemental_form: NutrientForm,
        oxide_form: NutrientForm,
    ) -> PkRecommended:
        assert value.extraction_method is not None  # checked by the caller
        base = f"crops.{inputs.crop.value}.phosphorus_potassium"
        method_key = value.extraction_method.value
        band = table.bands[index]
        band_label = table.band_label(band)
        response_label = table.response_legend[band.response]
        cell = table.cell(index)
        used = [
            UsedConstant.of(
                f"{base}.nutrients.{nutrient}.tables.{method_key}.bands[{index}].rate", cell
            ),
            UsedConstant.of(f"{base}.sample_depth_cm", cfg.sample_depth_cm),
        ]
        placeholder = any_placeholder(used)

        def soil_amount(form: NutrientForm) -> FormAmount:
            amount = units.convert_form(value.value_mg_per_kg, value.form, form)
            return FormAmount(
                form=form,
                amount=ExplainedNumber(
                    name=f"soil_test_{form.value}",
                    value=amount,
                    unit=f"mg {form.value}/kg",
                    explanation=explain.pk_soil_test_value(
                        form.value,
                        amount,
                        value.form.value,
                        value.value,
                        value.unit.value,
                        table.label,
                        soil.sample_date.isoformat(),
                    ),
                    uses_placeholder=False,
                ),
            )

        def rate_amount(form: NutrientForm) -> FormAmount:
            amount = units.convert_form(band.rate, table.rate_form, form)
            if form is table.rate_form:
                text = explain.pk_table_rate(
                    form.value,
                    amount,
                    table.label,
                    band_label,
                    band.response,
                    response_label,
                    cell,
                    table.assumes,
                    band.caution,
                )
            else:
                text = explain.pk_converted_rate(
                    form.value, amount, table.rate_form.value, band.rate, table.assumes
                )
            return FormAmount(
                form=form,
                amount=ExplainedNumber(
                    name=f"rate_{form.value}",
                    value=amount,
                    unit=f"kg {form.value}/ha",
                    explanation=text,
                    uses_placeholder=placeholder,
                ),
            )

        def total_amount(rate: FormAmount) -> FormAmount:
            total = rate.amount.value * inputs.area_ha
            return FormAmount(
                form=rate.form,
                amount=ExplainedNumber(
                    name=f"total_{rate.form.value}",
                    value=total,
                    unit=f"kg {rate.form.value}",
                    explanation=explain.pk_total(
                        rate.form.value, rate.amount.value, inputs.area_ha, total, table.assumes
                    ),
                    uses_placeholder=placeholder,
                ),
            )

        rate_elemental = rate_amount(elemental_form)
        rate_oxide = rate_amount(oxide_form)
        return PkRecommended(
            nutrient=nutrient,
            method_id=self.method_id,
            extraction_method=value.extraction_method,
            soil_test_elemental=soil_amount(elemental_form),
            soil_test_oxide=soil_amount(oxide_form),
            table_band=band_label,
            response=band.response,
            response_label=response_label,
            assumes=table.assumes,
            rate_form=table.rate_form,
            rate_elemental=rate_elemental,
            rate_oxide=rate_oxide,
            total_elemental=total_amount(rate_elemental),
            total_oxide=total_amount(rate_oxide),
            constants_used=used,
        )
