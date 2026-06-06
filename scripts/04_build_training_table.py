from __future__ import annotations

import pandas as pd

from lake_level_forecast.features import build_training_table
from lake_level_forecast.settings import REPO_ROOT, ensure_dirs, load_config


def main() -> None:
    ensure_dirs()
    cfg = load_config()
    model_cfg = cfg["model"]

    water_path = REPO_ROOT / "data/processed/nwcl1_water_event_windows.parquet"
    wind_path = REPO_ROOT / "data/processed/knew_wind_event_windows.parquet"
    if not water_path.exists():
        raise FileNotFoundError(f"Missing {water_path}. Run scripts/02_find_high_water_events.py first.")
    if not wind_path.exists():
        raise FileNotFoundError(f"Missing {wind_path}. Run scripts/03_fetch_knew_wind_for_events.py first.")

    water = pd.read_parquet(water_path)
    wind = pd.read_parquet(wind_path)
    table = build_training_table(
        water_events=water,
        wind_events=wind,
        resample_minutes=int(model_cfg["resample_minutes"]),
        lag_hours=list(model_cfg["wind_lag_hours"]),
        forecast_hours=list(model_cfg["forecast_hours"]),
    )

    out = REPO_ROOT / "data/processed/training_table.parquet"
    csv_out = REPO_ROOT / "data/processed/training_table_sample.csv"
    table.to_parquet(out, index=False)
    table.head(5000).to_csv(csv_out, index=False)
    print(f"Saved training table with {len(table):,} rows and {len(table.columns):,} columns to {out}")
    print(table.tail())


if __name__ == "__main__":
    main()
