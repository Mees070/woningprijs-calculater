import argparse
from pathlib import Path

import pandas as pd

from .config import MarketProfile
from .data import DatasetCleaner, MarketCalibrator


def calibrate_profile(data_path: Path, output_path: Path, min_count: int) -> None:
    df = pd.read_csv(data_path)
    cleaned = DatasetCleaner(df).clean()
    calibrator = MarketCalibrator(cleaned)

    profile = MarketProfile()
    profile.base_price_m2 = calibrator.median_price_per_m2()
    profile.city_base_price_m2 = calibrator.city_medians(min_count=min_count)
    profile.energy_label_adjustments = calibrator.category_adjustments(
        "energy_label", min_count=min_count, clamp=0.15
    )
    profile.build_type_adjustments = calibrator.category_adjustments(
        "build_type", min_count=min_count, clamp=0.12
    )
    profile.house_type_adjustments = calibrator.category_adjustments(
        "house_type_norm", min_count=min_count, clamp=0.2
    )
    profile.garden_adjustments = calibrator.category_adjustments(
        "garden_norm", min_count=min_count, clamp=0.08
    )
    profile.roof_adjustments = calibrator.category_adjustments(
        "roof_norm", min_count=min_count, clamp=0.08
    )
    profile.position_adjustments = calibrator.category_adjustments(
        "position_norm", min_count=min_count, clamp=0.08
    )
    profile.toilet_adjustments = calibrator.category_adjustments(
        "toilet_norm", min_count=min_count, clamp=0.08
    )
    profile.floors_adjustments = calibrator.category_adjustments(
        "floors_norm", min_count=min_count, clamp=0.08
    )
    ratio = cleaned["lot_size"] / cleaned["living_area"]
    profile.lot_size_ratio_median = float(ratio.replace([float("inf")], float("nan")).median())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    profile.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="House price calculator CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    calibrate_parser = subparsers.add_parser("calibrate", help="Calibrate profile.")
    calibrate_parser.add_argument("--data", default="data/raw_data.csv")
    calibrate_parser.add_argument("--output", default="configs/market_profile.json")
    calibrate_parser.add_argument("--min-count", type=int, default=50)

    args = parser.parse_args()

    if args.command == "calibrate":
        calibrate_profile(Path(args.data), Path(args.output), args.min_count)
        print(f"Saved market profile to {args.output}")


if __name__ == "__main__":
    main()
