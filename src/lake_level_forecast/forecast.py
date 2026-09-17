from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from lake_level_forecast.features import add_lagged_wind_features, add_targets, add_wind_components


def build_forecast_feature_row(
    current_water_level_ft: float,
    wind_forecast: pd.DataFrame,
    resample_minutes: int,
    lag_hours: list[int],
) -> pd.DataFrame:
    """Build a single feature row from recent/forecast wind input.

    The wind CSV should include datetime_utc, wind_speed_kt, wind_dir_deg, and optionally wind_gust_kt.
    For now, the row uses the last available wind time as forecast initialization.
    """
    df = wind_forecast.copy()
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    df = df.sort_values("datetime_utc")
    if "wind_gust_kt" not in df.columns:
        df["wind_gust_kt"] = df["wind_speed_kt"]
    if "air_temp_f" not in df.columns:
        df["air_temp_f"] = pd.NA
    if "pressure_mb" not in df.columns:
        df["pressure_mb"] = pd.NA

    df["event_id"] = "forecast"
    df["water_level_ft"] = current_water_level_ft
    df = add_wind_components(df)
    df = add_lagged_wind_features(df, lag_hours=lag_hours, minutes=resample_minutes)
    return df.tail(1).reset_index(drop=True)


def load_models(model_dir: str | Path) -> dict[int, dict]:
    models: dict[int, dict] = {}
    for path in Path(model_dir).glob("ridge_delta_*h.joblib"):
        payload = joblib.load(path)
        models[int(payload["horizon_hr"])] = payload
    return dict(sorted(models.items()))


def predict_water_levels(feature_row: pd.DataFrame, model_dir: str | Path) -> pd.DataFrame:
    rows = []
    for hr, payload in load_models(model_dir).items():
        model = payload["model"]
        features = payload["features"]
        missing = [c for c in features if c not in feature_row.columns]
        if missing:
            for col in missing:
                feature_row[col] = pd.NA
        delta = float(model.predict(feature_row[features])[0])
        current = float(feature_row["water_level_ft"].iloc[0])
        rows.append(
            {
                "horizon_hr": hr,
                "current_water_level_ft_mllw": current,
                "predicted_delta_ft": delta,
                "forecast_water_level_ft_mllw": current + delta,
            }
        )
    return pd.DataFrame(rows)
