from typing import Dict

import pandas as pd

from .utils import (
    coerce_number,
    normalize_energy_label,
    normalize_floors,
    normalize_garden,
    normalize_house_type,
    normalize_position,
    normalize_toilet,
    parse_rooms,
)


class DatasetCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def clean(self) -> pd.DataFrame:
        df = self.df
        df["price"] = df["Price"].apply(coerce_number)
        df["living_area"] = df["Living space size (m2)"].apply(coerce_number)
        df["lot_size"] = df["Lot size (m2)"].apply(coerce_number)
        df["build_year"] = df["Build year"].apply(coerce_number)
        df["rooms"] = df["Rooms"].apply(parse_rooms)
        df["energy_label"] = df["Energy label"].apply(normalize_energy_label)
        df["build_type"] = df["Build type"].astype(str).str.strip()
        df["house_type"] = df["House type"].astype(str).str.strip()
        df["garden"] = df["Garden"].astype(str).str.strip()
        df["position"] = df["Position"].astype(str).str.strip()
        df["toilet"] = df["Toilet"].astype(str).str.strip()
        df["floors"] = df["Floors"].astype(str).str.strip()
        df["house_type_norm"] = df["house_type"].apply(normalize_house_type)
        df["garden_norm"] = df["garden"].apply(normalize_garden)
        df["position_norm"] = df["position"].apply(normalize_position)
        df["toilet_norm"] = df["toilet"].apply(normalize_toilet)
        df["floors_norm"] = df["floors"].apply(normalize_floors)
        df["city"] = df["City"].astype(str).str.strip()
        df["neighborhood_price_m2"] = df["Estimated neighbourhood price per m2"].apply(
            coerce_number
        )
        df = df.dropna(subset=["price", "living_area"]).copy()
        df["price_per_m2"] = df["price"] / df["living_area"]
        return df


class MarketCalibrator:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def median_price_per_m2(self) -> float:
        return float(self.df["price_per_m2"].median())

    def city_medians(self, min_count: int) -> Dict[str, float]:
        grouped = self.df.groupby("city")["price_per_m2"]
        counts = grouped.count()
        medians = grouped.median()
        filtered = medians[counts >= min_count]
        return {city: float(value) for city, value in filtered.items()}

    def category_adjustments(self, column: str, min_count: int, clamp: float) -> Dict[str, float]:
        grouped = self.df.groupby(column)["price_per_m2"]
        counts = grouped.count()
        medians = grouped.median()
        base = self.median_price_per_m2()
        adjustments = {}
        for category, median in medians.items():
            if counts[category] < min_count:
                continue
            ratio = (median / base) - 1.0
            ratio = max(-clamp, min(clamp, ratio))
            adjustments[str(category)] = float(ratio)
        return adjustments
