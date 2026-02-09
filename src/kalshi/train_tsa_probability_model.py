"""Train a simple sklearn logistic model for TSA contract yes-probability."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import contract_probability_model

DEFAULT_LEAN_CORE_FEATURES = [
    "strike_distance_pct",
    "abs_strike_distance_pct",
    "day_7_trend",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train TSA contract yes-probability logistic model.")
    parser.add_argument("--dataset-csv", type=Path, required=True, help="Contract-level training dataset CSV")
    parser.add_argument("--target-col", default="y_yes_win", help="Binary target column")
    parser.add_argument("--run-date-col", default="run_date", help="Run-date column used for walk-forward windows")
    parser.add_argument(
        "--features",
        default=None,
        help=(
            "Optional comma-separated feature names; defaults to lean_core: "
            "strike_distance_pct,abs_strike_distance_pct,day_7_trend"
        ),
    )
    parser.add_argument("--train-weeks", type=int, default=52, help="Number of weekly run_dates per train fold")
    parser.add_argument("--val-weeks", type=int, default=8, help="Number of weekly run_dates per validation fold")
    parser.add_argument("--step-weeks", type=int, default=4, help="Number of weeks to advance between folds")
    parser.add_argument(
        "--out-model",
        type=Path,
        default=contract_probability_model.DEFAULT_MODEL_BUNDLE,
        help="Output path for sklearn joblib model",
    )
    parser.add_argument(
        "--out-metadata",
        type=Path,
        default=None,
        help="Optional output metadata JSON path (defaults next to model)",
    )
    return parser.parse_args()


def _build_pipeline() -> Pipeline:
    """Return a simple numeric logistic pipeline."""
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000, solver="lbfgs")),
        ]
    )


def _default_feature_columns(df: pd.DataFrame, target_col: str, run_date_col: str) -> List[str]:
    """Return the default lean-core features used for production training."""
    _ = target_col, run_date_col
    missing = [column for column in DEFAULT_LEAN_CORE_FEATURES if column not in df.columns]
    if missing:
        raise ValueError(
            "Default lean-core features missing from dataset: "
            f"{missing}. Provide --features explicitly or rebuild dataset."
        )
    return list(DEFAULT_LEAN_CORE_FEATURES)


def _walk_forward_splits(
    run_dates: Sequence[pd.Timestamp],
    train_weeks: int,
    val_weeks: int,
    step_weeks: int,
) -> List[Tuple[List[pd.Timestamp], List[pd.Timestamp]]]:
    """Return walk-forward fold date lists using sorted unique run_dates."""
    if train_weeks <= 0 or val_weeks <= 0 or step_weeks <= 0:
        raise ValueError("train_weeks, val_weeks, and step_weeks must be > 0.")
    if len(run_dates) < (train_weeks + val_weeks):
        return []
    folds: List[Tuple[List[pd.Timestamp], List[pd.Timestamp]]] = []
    start = train_weeks
    while start + val_weeks <= len(run_dates):
        train_dates = list(run_dates[start - train_weeks:start])
        val_dates = list(run_dates[start:start + val_weeks])
        folds.append((train_dates, val_dates))
        start += step_weeks
    return folds


def train_from_dataset(
    dataset_csv: Path,
    target_col: str = "y_yes_win",
    run_date_col: str = "run_date",
    feature_columns: Optional[Sequence[str]] = None,
    train_weeks: int = 52,
    val_weeks: int = 8,
    step_weeks: int = 4,
    out_model: Path = contract_probability_model.DEFAULT_MODEL_BUNDLE,
    out_metadata: Optional[Path] = None,
) -> Dict[str, object]:
    """Train walk-forward logistic model and persist model + schema + metadata."""
    df = pd.read_csv(dataset_csv)
    if target_col not in df.columns:
        raise ValueError(f"Missing target column: {target_col}")
    if run_date_col not in df.columns:
        raise ValueError(f"Missing run-date column: {run_date_col}")

    df = df.copy()
    df[run_date_col] = pd.to_datetime(df[run_date_col], errors="raise")
    df[target_col] = df[target_col].astype(int)

    features = list(feature_columns) if feature_columns else _default_feature_columns(df, target_col, run_date_col)
    run_dates = sorted(df[run_date_col].dropna().unique())
    folds = _walk_forward_splits(run_dates, train_weeks=train_weeks, val_weeks=val_weeks, step_weeks=step_weeks)

    oos_rows: List[pd.DataFrame] = []
    fold_metrics: List[Dict[str, object]] = []
    for fold_idx, (train_dates, val_dates) in enumerate(folds, start=1):
        train_mask = df[run_date_col].isin(train_dates)
        val_mask = df[run_date_col].isin(val_dates)
        train_df = df.loc[train_mask]
        val_df = df.loc[val_mask]
        if train_df.empty or val_df.empty:
            continue
        if train_df[target_col].nunique() < 2:
            # A one-class train fold cannot fit logistic regression.
            continue

        model = _build_pipeline()
        model.fit(train_df[features], train_df[target_col])
        probs = model.predict_proba(val_df[features])[:, 1]
        val_pred = val_df[[run_date_col, target_col]].copy()
        val_pred["prob_yes"] = probs
        val_pred["fold"] = fold_idx
        oos_rows.append(val_pred)

        fold_result: Dict[str, object] = {
            "fold": fold_idx,
            "train_rows": int(len(train_df)),
            "val_rows": int(len(val_df)),
            "train_date_start": train_dates[0].date().isoformat(),
            "train_date_end": train_dates[-1].date().isoformat(),
            "val_date_start": val_dates[0].date().isoformat(),
            "val_date_end": val_dates[-1].date().isoformat(),
            "brier": float(brier_score_loss(val_df[target_col], probs)),
            "logloss": float(log_loss(val_df[target_col], probs, labels=[0, 1])),
        }
        if val_df[target_col].nunique() > 1:
            fold_result["auc"] = float(roc_auc_score(val_df[target_col], probs))
        else:
            fold_result["auc"] = None
        fold_metrics.append(fold_result)

    final_model = _build_pipeline()
    if df[target_col].nunique() < 2:
        raise ValueError("Training dataset target has a single class; cannot fit logistic regression.")
    final_model.fit(df[features], df[target_col])
    contract_probability_model.save_sklearn_bundle(
        model=final_model,
        feature_names=features,
        model_bundle_path=out_model,
        schema_version="v1",
        model_version="logistic-baseline",
    )

    oos_df = pd.concat(oos_rows, ignore_index=True) if oos_rows else pd.DataFrame(columns=[run_date_col, target_col, "prob_yes", "fold"])
    aggregate_metrics: Dict[str, Optional[float]] = {
        "oos_rows": float(len(oos_df)),
    }
    if not oos_df.empty:
        y_true = oos_df[target_col].astype(int).to_numpy()
        y_prob = oos_df["prob_yes"].astype(float).to_numpy()
        aggregate_metrics["brier"] = float(brier_score_loss(y_true, y_prob))
        aggregate_metrics["logloss"] = float(log_loss(y_true, y_prob, labels=[0, 1]))
        aggregate_metrics["auc"] = float(roc_auc_score(y_true, y_prob)) if np.unique(y_true).size > 1 else None
    else:
        aggregate_metrics["brier"] = None
        aggregate_metrics["logloss"] = None
        aggregate_metrics["auc"] = None

    metadata = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "dataset_csv": str(dataset_csv.resolve()),
        "rows": int(len(df)),
        "target_col": target_col,
        "run_date_col": run_date_col,
        "feature_columns": features,
        "walk_forward": {
            "train_weeks": train_weeks,
            "val_weeks": val_weeks,
            "step_weeks": step_weeks,
            "folds_used": len(fold_metrics),
        },
        "fold_metrics": fold_metrics,
        "aggregate_oos_metrics": aggregate_metrics,
        "model_path": str(out_model.resolve()),
        "schema_path": str(out_model.with_suffix(".schema.json").resolve()),
    }
    metadata_path = out_metadata or out_model.with_suffix(".metadata.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))
    return metadata


def main() -> None:
    args = _parse_args()
    features = [value.strip() for value in args.features.split(",")] if args.features else None
    metadata = train_from_dataset(
        dataset_csv=args.dataset_csv,
        target_col=args.target_col,
        run_date_col=args.run_date_col,
        feature_columns=features,
        train_weeks=args.train_weeks,
        val_weeks=args.val_weeks,
        step_weeks=args.step_weeks,
        out_model=args.out_model,
        out_metadata=args.out_metadata,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
