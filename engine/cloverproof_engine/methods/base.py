"""The pluggable nutrient-method interface.

A method turns inputs + an already-loaded pack into its result: a `NutrientResult` for
nitrogen, `PkResults` for phosphorus and potassium. Methods are selected by id from the
pack (`crops.<crop>.<nutrient>.method`), so country differences live in packs, never in
code forks.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import Pack


class NutrientMethod[ResultT](ABC):
    method_id: ClassVar[str]
    nutrient: ClassVar[str]

    @abstractmethod
    def calculate(self, inputs: RecommendationInput, pack: Pack) -> ResultT:
        """Pure calculation: no I/O, no clock, no randomness."""
