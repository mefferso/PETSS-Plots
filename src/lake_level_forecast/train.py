from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from lake_level_forecast.features import feature_columns


def train_models(
    table: pd.DataFrame,
    forecast_hours: list[int],
    split_date: str,
    model_dir: str | Path,
    plot_dir: str | Path,
) -> pd.DataFrame:
    model_path = Path(model_dir)
    plot_path = Path(plot_dir)
    model_path.mkdir(parents=True, exist_ok=True)
    plot_path.mkdir(parents=True, exist_ok=True)

    table = table.copy()
    table["datetime_utc"] = pd.to_datetime(table["datetime_utc"], utc=True)
    split_ts = pd.Timestamp(split_date, tz="UTC")
    features = feature_columns(table)

    rows: list[dict[str, Any]] = []
    for hr in forecast_hours:
        target = f"delta_{hr}h_ft"
        data = table.dropna(subset=[target]).copy()
        if data.empty:
            rows.append({"horizon_hr": hr, "error": "no training rows"})
            continue

        train = data[data["datetime_utc"] < split_ts]
        test = data[data["datetime_utc"] >= split_ts]
        if len(test) < 20:
            # Fallback if the split leaves too little recent data.
            cutoff = int(len(data) * 0.8)
            train = data.iloc[:cutoff]
            test = data.iloc[cutoff:]

        X_train = train[features]
        y_train = train[target]
        X_test = test[features]
        y_test = test[target]

        model = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("ridge", RidgeCV(alphas=np.logspace(-3, 3, 25))),
            ]
        )
        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        mae = mean_absolute_error(y_test, pred)
        rmse = mean_squared_error(y_test, pred, squared=False)
        r2 = r2_score(y_test, pred) if len(y_test) > 1 else np.nan

        # Persistence baseline for water level is delta=0.
        persistence_pred = np.zeros_like(y_test, dtype=float)
        persistence_mae = mean_absolute_error(y_test, persistence_pred)
        persistence_rmse = mean_squared_error(y_test, persistence_pred, squared=False)

        payload = {
            "model": model,
            "features": features,
            "target": target,
            "horizon_hr": hr,
        }
        joblib.dump(payload, model_path / f"ridge_delta_{hr}h.joblib")

        plt.figure(figsize=(7, 7))
        plt.scatter(y_test, pred, alpha=0.35)
        lim_min = min(float(np.nanmin(y_test)), float(np.nanmin(pred)))
        lim_max = max(float(np.nanmax(y_test)), float(np.nanmax(pred)))
        plt.plot([lim_min, lim_max], [lim_min, lim_max])
        plt.xlabel(f"Observed {target}")
        plt.ylabel(f"Predicted {target}")
        plt.title(f"NWCL1 forecast delta +{hr}h")
        plt.tight_layout()
        plt.savefig(plot_path / f"predicted_vs_observed_delta_{hr}h.png", dpi=150)
        plt.close()

        rows.append(
            {
                "horizon_hr": hr,
                "n_train": len(train),
                "n_test": len(test),
                "mae_ft": mae,
                "rmse_ft": rmse,
                "r2": r2,
                "persistence_mae_ft": persistence_mae,
                "persistence_rmse_ft": persistence_rmse,
                "skill_vs_persistence_mae_pct": 100 * (1 - mae / persistence_mae) if persistence_mae else np.nan,
                "model_file": str(model_path / f"ridge_delta_{hr}h.joblib"),
            }
        )

    return pd.DataFrame(rows)
