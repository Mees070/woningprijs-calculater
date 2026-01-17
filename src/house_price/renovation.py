from dataclasses import dataclass

from .config import MarketProfile
from .utils import normalize_energy_label


@dataclass
class RenovationScenario:
    budget: float = 0.0
    energy_label_before: str = ""
    energy_label_after: str = ""

    def label_uplift(self, profile: MarketProfile) -> float:
        before = normalize_energy_label(self.energy_label_before)
        after = normalize_energy_label(self.energy_label_after)
        if not before or not after:
            return 0.0
        order = {"G": 1, "F": 2, "E": 3, "D": 4, "C": 5, "B": 6, "A": 7, "A1": 8, "A2": 9, "A3": 10, "A4": 11}
        before_score = order.get(before, 0)
        after_score = order.get(after, 0)
        if after_score <= before_score:
            return 0.0
        steps = after_score - before_score
        uplift = steps * profile.renovation_label_step_uplift
        return min(profile.renovation_label_cap, uplift)
