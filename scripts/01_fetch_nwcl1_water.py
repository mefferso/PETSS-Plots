from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from lake_level_forecast.coops import fetch_water_level_archive
from lake_level_forecast.settings import REPO_ROOT, ensure_dirs, load_config


def main() -> None:
    ensure_dirs()
    cfg = load_config()
    water_cfg = cfg["water_level"]

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365.25 * int(water_cfg["years_back"]))

    print(f"Fetching NWCL1 water level from {start:%Y-%m-%d} to {end:%Y-%m-%d}...")
    df = fetch_water_level_archive(
        station=water_cfg["station_id"],
        start=start,
        end=end,
        datum=water_cfg["datum"],
        units=water_cfg["units"],
        time_zone=water_cfg["time_zone"],
        raw_dir=REPO_ROOT / "data/raw/coops",
    )

    out = REPO_ROOT / "data/processed/nwcl1_water_level_5yr_mllw.parquet"
    csv_out = REPO_ROOT / "data/processed/nwcl1_water_level_5yr_mllw.csv"
    df.to_parquet(out, index=False)
    df.to_csv(csv_out, index=False)
    print(f"Saved {len(df):,} water-level rows to {out}")
    print(df.tail())


if __name__ == "__main__":
    main()
