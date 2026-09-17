from __future__ import annotations

import pandas as pd

from lake_level_forecast.settings import REPO_ROOT, ensure_dirs, load_config
from lake_level_forecast.train import train_models


def main() -> None:
    ensure_dirs()
    cfg = load_config()
    model_cfg = cfg["model"]

    table_path = REPO_ROOT / "data/processed/training_table.parquet"
    if not table_path.exists():
        raise FileNotFoundError(f"Missing {table_path}. Run scripts/04_build_training_table.py first.")

    table = pd.read_parquet(table_path)
    metrics = train_models(
        table=table,
        forecast_hours=list(model_cfg["forecast_hours"]),
        split_date=str(model_cfg["train_test_split_date"]),
        model_dir=REPO_ROOT / "models",
        plot_dir=REPO_ROOT / "outputs/plots",
    )

    out = REPO_ROOT / "outputs/tables/model_metrics.csv"
    metrics.to_csv(out, index=False)
    print(f"Saved model metrics to {out}")
    print(metrics)


if __name__ == "__main__":
    main()
