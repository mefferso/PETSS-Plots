from __future__ import annotations

import argparse

import pandas as pd

from lake_level_forecast.coops import fetch_latest_water_level
from lake_level_forecast.forecast import build_forecast_feature_row, predict_water_levels
from lake_level_forecast.settings import REPO_ROOT, ensure_dirs, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Forecast NWCL1 water level from KNEW wind forecast CSV.")
    parser.add_argument("--wind-csv", required=True, help="CSV with datetime_utc, wind_speed_kt, wind_dir_deg, optional wind_gust_kt")
    parser.add_argument("--current-water-level-ft", type=float, default=None, help="Override latest NWCL1 water level in ft MLLW")
    args = parser.parse_args()

    ensure_dirs()
    cfg = load_config()
    water_cfg = cfg["water_level"]
    model_cfg = cfg["model"]

    if args.current_water_level_ft is None:
        latest = fetch_latest_water_level(station=water_cfg["station_id"], datum=water_cfg["datum"])
        if latest.empty:
            raise RuntimeError("Could not fetch latest NWCL1 water level.")
        current_water_level_ft = float(latest.sort_values("datetime_utc").tail(1)["water_level_ft"].iloc[0])
    else:
        current_water_level_ft = args.current_water_level_ft

    wind_fcst = pd.read_csv(args.wind_csv)
    row = build_forecast_feature_row(
        current_water_level_ft=current_water_level_ft,
        wind_forecast=wind_fcst,
        resample_minutes=int(model_cfg["resample_minutes"]),
        lag_hours=list(model_cfg["wind_lag_hours"]),
    )
    forecast = predict_water_levels(row, REPO_ROOT / "models")

    out = REPO_ROOT / "outputs/tables/latest_forecast.csv"
    forecast.to_csv(out, index=False)
    print(forecast)
    print(f"Saved forecast to {out}")


if __name__ == "__main__":
    main()
