from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv

from lake_level_forecast.settings import REPO_ROOT, ensure_dirs, load_config
from lake_level_forecast.synoptic import fetch_wind_for_events


def main() -> None:
    ensure_dirs()
    load_dotenv(REPO_ROOT / ".env")
    cfg = load_config()
    wind_cfg = cfg["wind"]

    token = os.getenv("SYNOPTIC_TOKEN")
    if not token:
        raise RuntimeError("Missing SYNOPTIC_TOKEN. Add it to .env locally or GitHub Actions secrets.")

    events_path = REPO_ROOT / "data/processed/nwcl1_high_water_events.csv"
    if not events_path.exists():
        raise FileNotFoundError(f"Missing {events_path}. Run scripts/02_find_high_water_events.py first.")

    events = pd.read_csv(events_path, parse_dates=["event_start_utc", "event_end_utc", "window_start_utc", "window_end_utc", "peak_time_utc"])
    print(f"Fetching {wind_cfg['station_id']} wind for {len(events)} event windows...")
    wind = fetch_wind_for_events(
        events=events,
        station=wind_cfg["station_id"],
        token=token,
        raw_dir=REPO_ROOT / "data/raw/synoptic",
    )

    out = REPO_ROOT / "data/processed/knew_wind_event_windows.parquet"
    csv_out = REPO_ROOT / "data/processed/knew_wind_event_windows.csv"
    wind.to_parquet(out, index=False)
    wind.to_csv(csv_out, index=False)
    print(f"Saved {len(wind):,} wind rows to {out}")
    print(wind.tail())


if __name__ == "__main__":
    main()
