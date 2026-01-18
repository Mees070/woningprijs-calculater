from typing import Dict, Optional

import numpy as np

from .config import MarketProfile
from .renovation import RenovationScenario
from .utils import coerce_number, normalize_energy_label


class PriceEstimator:
    def __init__(self, profile: MarketProfile):
        self.profile = profile

    def market_multiplier(self, years_forward: int = 0) -> float:
        years = max(0, years_forward)
        return (1.0 + self.profile.annual_growth_rate) ** years

    def base_price_m2(self, features: dict) -> float:
        neighborhood_price = coerce_number(features.get("neighborhood_price_m2"))
        city = str(features.get("city", "")).strip()
        micro_location = str(features.get("micro_location", "")).strip()
        city_price = self.profile.city_base_price_m2.get(city)
        base = city_price if city_price else self.profile.base_price_m2
        if neighborhood_price and not np.isnan(neighborhood_price):
            weight = self.profile.neighborhood_price_weight
            base = (weight * neighborhood_price) + ((1 - weight) * base)
        micro_uplift = self.profile.micro_segment_base_uplift.get(micro_location, 0.0)
        base = base * (1.0 + micro_uplift)
        return float(base)

    def small_home_uplift(self, living_area: float) -> float:
        reference = self.profile.small_home_reference_m2
        if reference <= 50:
            return 0.0
        if living_area >= reference:
            return 0.0
        ratio = (reference - living_area) / (reference - 50.0)
        uplift = ratio * self.profile.small_home_uplift_at_50m2
        return float(min(self.profile.small_home_uplift_cap, max(0.0, uplift)))

    def room_adjustment(self, features: dict) -> float:
        living_area = coerce_number(features.get("living_area"))
        rooms = coerce_number(features.get("rooms"))
        if np.isnan(living_area) or np.isnan(rooms):
            return 0.0
        expected_rooms = max(1.0, living_area / self.profile.room_area_m2)
        diff = rooms - expected_rooms
        adjustment = diff * self.profile.room_adjustment_per_room
        overcrowding_threshold = max(0.0, self.profile.room_overcrowding_threshold)
        if diff > overcrowding_threshold:
            overcrowding_excess = diff - overcrowding_threshold
            adjustment -= overcrowding_excess * self.profile.room_overcrowding_penalty_per_room
        cap = abs(self.profile.room_adjustment_cap)
        return float(max(-cap, min(cap, adjustment)))

    def category_adjustment(self, value: Optional[str], mapping: Dict[str, float]) -> float:
        if not value:
            return 0.0
        key = str(value).strip()
        return float(mapping.get(key, 0.0))

    def garden_adjustment(self, features: dict) -> float:
        garden_area = coerce_number(features.get("garden_area"))
        if np.isnan(garden_area) or garden_area < 10:
            return 0.0
        house_type = str(features.get("house_type", "")).strip()
        mapping = (
            self.profile.garden_adjustments_apartment
            if house_type == "Apartment"
            else self.profile.garden_adjustments_house
        )
        if garden_area < 25:
            key = "10-25"
        elif garden_area < 50:
            key = "25-50"
        else:
            key = "50+"
        return float(mapping.get(key, 0.0))

    def estimate(self, features: dict, years_forward: int = 0) -> dict:
        living_area = coerce_number(features.get("living_area"))
        if np.isnan(living_area):
            raise ValueError("living_area is required for estimation.")

        base_price_m2 = self.base_price_m2(features)
        full_area = max(0.0, self.profile.area_full_price_m2)
        extra_weight = max(0.0, min(1.0, self.profile.area_extra_weight))
        if living_area <= full_area:
            effective_area = living_area
        else:
            effective_area = full_area + (living_area - full_area) * extra_weight
        base_value = effective_area * base_price_m2
        micro_location = str(features.get("micro_location", "")).strip()

        adjustments = {
            "energy_label": self.category_adjustment(
                normalize_energy_label(features.get("energy_label")),
                self.profile.energy_label_adjustments,
            ),
            "build_type": self.category_adjustment(
                features.get("build_type"), self.profile.build_type_adjustments
            ),
            "house_type": 0.0,
            "garden": self.garden_adjustment(features),
            "position": 0.0,
            "bathrooms": self.category_adjustment(
                features.get("bathrooms"), self.profile.bathroom_adjustments
            ),
            "toilets": self.category_adjustment(
                features.get("toilets"), self.profile.toilet_count_adjustments
            ),
            "condition": self.category_adjustment(
                features.get("condition"), self.profile.condition_adjustments
            ),
            "build_year": self.build_year_adjustment(features),
            "rooms": self.room_adjustment(features),
            "lot_size": self.lot_size_adjustment(features),
            "small_home": self.small_home_uplift(living_area),
        }
        house_type = features.get("house_type")
        neutralize_house_types = self.profile.micro_location_house_type_neutralize.get(
            micro_location, []
        )
        if house_type not in neutralize_house_types:
            adjustments["house_type"] = self.category_adjustment(
                house_type, self.profile.house_type_adjustments
            )
        if micro_location not in self.profile.micro_location_disable_position_adjustment:
            adjustments["position"] = self.category_adjustment(
                features.get("position"), self.profile.position_adjustments
            )

        total_adjustment = sum(adjustments.values())
        total_adjustment = max(self.profile.min_adjustment, min(self.profile.max_adjustment, total_adjustment))
        estimate = base_value * (1.0 + total_adjustment) * self.market_multiplier(years_forward)
        estimate_range = self._estimate_range(estimate, total_adjustment)

        return {
            "base_price_m2": float(base_price_m2),
            "living_area": float(living_area),
            "base_value": float(base_value),
            "adjustments": adjustments,
            "total_adjustment": float(total_adjustment),
            "market_multiplier": float(self.market_multiplier(years_forward)),
            "estimate": float(estimate),
            "estimate_range": estimate_range,
        }

    def lot_size_adjustment(self, features: dict) -> float:
        micro_location = str(features.get("micro_location", "")).strip()
        if micro_location in self.profile.micro_location_disable_lot_size_adjustment:
            return 0.0
        lot_size = coerce_number(features.get("lot_size"))
        living_area = coerce_number(features.get("living_area"))
        if np.isnan(lot_size) or np.isnan(living_area) or living_area <= 0:
            return 0.0
        if self.profile.lot_size_ratio_median <= 0:
            return 0.0
        ratio = lot_size / living_area
        delta = (ratio / self.profile.lot_size_ratio_median) - 1.0
        adjustment = delta * self.profile.lot_size_ratio_weight
        clamp = self.profile.lot_size_ratio_clamp
        return float(max(-clamp, min(clamp, adjustment)))

    def build_year_adjustment(self, features: dict) -> float:
        year = coerce_number(features.get("build_year"))
        if np.isnan(year):
            return 0.0
        for bucket in self.profile.build_year_buckets:
            min_year = bucket.get("min_year")
            max_year = bucket.get("max_year")
            if min_year is not None and year < min_year:
                continue
            if max_year is not None and year > max_year:
                continue
            return float(bucket.get("adjustment", 0.0))
        return 0.0

    def estimate_with_renovation(
        self,
        features: dict,
        scenario: RenovationScenario,
        years_forward: int = 0,
    ) -> dict:
        base_features = dict(features)
        if scenario.energy_label_before:
            base_features["energy_label"] = scenario.energy_label_before
        base = self.estimate(base_features, years_forward=years_forward)
        base_value = base["estimate"]

        uplift_from_budget = 0.0
        if scenario.budget > 0 and base_value > 0:
            ratio = scenario.budget / base_value
            linear_uplift = ratio * self.profile.renovation_roi
            saturation = max(0.01, self.profile.renovation_roi_saturation)
            uplift_from_budget = linear_uplift / (1.0 + (ratio / saturation))

        before_label = normalize_energy_label(scenario.energy_label_before)
        after_label = normalize_energy_label(scenario.energy_label_after)
        before_adj = self.profile.energy_label_adjustments.get(before_label, 0.0)
        after_adj = self.profile.energy_label_adjustments.get(after_label, 0.0)
        uplift_from_label = max(0.0, after_adj - before_adj)
        uplift_from_label = min(self.profile.renovation_label_cap, uplift_from_label)
        uplift = uplift_from_budget + uplift_from_label
        uplift = min(self.profile.renovation_cap, max(0.0, uplift))

        renovated_value = base_value * (1.0 + uplift)
        renovated_range = self._estimate_range(renovated_value, base["total_adjustment"])
        base["renovation"] = {
            "budget": float(scenario.budget),
            "label_uplift": float(uplift_from_label),
            "roi_uplift": float(uplift_from_budget),
            "total_uplift": float(uplift),
            "renovated_value": float(renovated_value),
            "renovated_range": renovated_range,
        }
        return base

    def _estimate_range(self, estimate: float, total_adjustment: float) -> dict:
        uncertainty = self.profile.estimate_uncertainty_base + (
            abs(total_adjustment) * self.profile.estimate_uncertainty_per_adjustment
        )
        uncertainty = max(0.02, min(0.25, uncertainty))
        low = estimate * (1.0 - uncertainty)
        high = estimate * (1.0 + uncertainty)
        return {
            "low": float(low),
            "high": float(high),
            "uncertainty_pct": float(uncertainty),
        }
