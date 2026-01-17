import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class MarketProfile:
    reference_year: int = 2022
    current_year: int = 2026
    annual_growth_rate: float = 0.04
    base_price_m2: float = 3500.0
    city_base_price_m2: Dict[str, float] = field(default_factory=dict)
    neighborhood_price_weight: float = 0.7
    room_area_m2: float = 30.0
    room_adjustment_per_room: float = 0.02
    max_adjustment: float = 0.25
    min_adjustment: float = -0.2
    energy_label_adjustments: Dict[str, float] = field(default_factory=dict)
    build_type_adjustments: Dict[str, float] = field(default_factory=dict)
    house_type_adjustments: Dict[str, float] = field(default_factory=dict)
    garden_adjustments: Dict[str, float] = field(default_factory=dict)
    roof_adjustments: Dict[str, float] = field(default_factory=dict)
    position_adjustments: Dict[str, float] = field(default_factory=dict)
    toilet_adjustments: Dict[str, float] = field(default_factory=dict)
    floors_adjustments: Dict[str, float] = field(default_factory=dict)
    lot_size_ratio_median: float = 0.0
    lot_size_ratio_weight: float = 0.15
    lot_size_ratio_clamp: float = 0.06
    build_year_buckets: list = field(default_factory=list)
    area_full_price_m2: float = 80.0
    area_extra_weight: float = 0.7
    renovation_roi: float = 0.6
    renovation_cap: float = 0.2
    renovation_label_step_uplift: float = 0.02
    renovation_label_cap: float = 0.08
    renovation_roi_saturation: float = 0.08
    renovation_category_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "kitchen": 0.7,
            "bathroom": 0.8,
            "insulation": 1.2,
            "roof_windows": 1.1,
            "exterior": 0.6,
            "other": 1.0,
        }
    )
    estimate_uncertainty_base: float = 0.06
    estimate_uncertainty_per_adjustment: float = 0.5

    @classmethod
    def load(cls, path: Path) -> "MarketProfile":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")
