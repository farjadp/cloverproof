"""The pluggable nutrient-method interface.

A method turns inputs + an already-loaded pack into a `NutrientResult`.
Methods are selected by id from the pack (`crops.<crop>.<nutrient>.method`),
so country differences live in packs, never in code forks.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from cloverproof_engine.models import RecommendationInput
from cloverproof_engine.pack import Pack
from cloverproof_engine.results import NutrientResult


class NutrientMethod(ABC):
    method_id: ClassVar[str]
    nutrient: ClassVar[str]

    @abstractmethod
    def calculate(self, inputs: RecommendationInput, pack: Pack) -> NutrientResult:
        """Pure calculation: no I/O, no clock, no randomness."""
