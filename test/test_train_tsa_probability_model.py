import json

import pandas as pd

from src.kalshi import train_tsa_probability_model as trainer


def test_train_from_dataset_writes_model_and_metadata(tmp_path):
    dataset_path = tmp_path / "contract_dataset.csv"
    df = pd.DataFrame(
        {
            "run_date": pd.to_datetime(
                [
                    "2025-01-05",
                    "2025-01-12",
                    "2025-01-19",
                    "2025-01-26",
                    "2025-02-02",
                    "2025-02-09",
                    "2025-02-16",
                    "2025-02-23",
                ]
            ),
            "strike_distance_pct": [-0.08, -0.04, -0.01, 0.01, 0.03, 0.06, 0.09, 0.12],
            "day_1_trend": [0.97, 0.99, 1.00, 1.01, 1.02, 1.03, 1.05, 1.06],
            "day_7_trend": [0.98, 0.99, 1.00, 1.01, 1.01, 1.02, 1.03, 1.04],
            "y_yes_win": [0, 0, 0, 1, 1, 1, 1, 1],
        }
    )
    df.to_csv(dataset_path, index=False)

    model_path = tmp_path / "tsa_yes_probability_model.joblib"
    metadata_path = tmp_path / "tsa_yes_probability_model.metadata.json"
    metadata = trainer.train_from_dataset(
        dataset_csv=dataset_path,
        feature_columns=["strike_distance_pct", "day_1_trend", "day_7_trend"],
        train_weeks=4,
        val_weeks=2,
        step_weeks=2,
        out_model=model_path,
        out_metadata=metadata_path,
    )

    assert model_path.exists()
    assert model_path.with_suffix(".schema.json").exists()
    assert metadata_path.exists()
    assert metadata["walk_forward"]["folds_used"] >= 1
    saved = json.loads(metadata_path.read_text())
    assert saved["model_path"].endswith(".joblib")
    first_fold = saved["fold_metrics"][0]
    assert "train_date_start" in first_fold
    assert "train_date_end" in first_fold
    assert "val_date_start" in first_fold
    assert "val_date_end" in first_fold


def test_train_from_dataset_uses_lean_core_defaults(tmp_path):
    dataset_path = tmp_path / "contract_dataset.csv"
    df = pd.DataFrame(
        {
            "run_date": pd.to_datetime(
                [
                    "2025-01-05",
                    "2025-01-12",
                    "2025-01-19",
                    "2025-01-26",
                    "2025-02-02",
                    "2025-02-09",
                    "2025-02-16",
                    "2025-02-23",
                ]
            ),
            "strike_distance_pct": [-0.08, -0.04, -0.01, 0.01, 0.03, 0.06, 0.09, 0.12],
            "abs_strike_distance_pct": [0.08, 0.04, 0.01, 0.01, 0.03, 0.06, 0.09, 0.12],
            "day_7_trend": [0.98, 0.99, 1.00, 1.01, 1.01, 1.02, 1.03, 1.04],
            "y_yes_win": [0, 0, 0, 1, 1, 1, 1, 1],
        }
    )
    df.to_csv(dataset_path, index=False)

    model_path = tmp_path / "tsa_yes_probability_model.joblib"
    metadata = trainer.train_from_dataset(
        dataset_csv=dataset_path,
        train_weeks=4,
        val_weeks=2,
        step_weeks=2,
        out_model=model_path,
    )

    assert metadata["feature_columns"] == trainer.DEFAULT_LEAN_CORE_FEATURES
