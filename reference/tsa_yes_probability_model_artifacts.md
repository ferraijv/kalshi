# TSA Yes-Probability Model Artifact Guide

This guide explains the model artifacts used for contract probability inference:

- `src/data/models/tsa_yes_probability_model.joblib`
- `src/data/models/tsa_yes_probability_model.schema.json`
- `src/data/models/tsa_yes_probability_model.metadata.json`

The objective is auditability before live trading.

## What each file contains

### Model (`.joblib`)
- Trained sklearn pipeline (preprocessing + logistic model).
- Produces `P(YES wins)` for each contract row.

### Schema (`.schema.json`)
- Input contract for inference.
- Defines required `feature_names` and versions.

### Metadata (`.metadata.json`)
- Full training run record.
- Includes dataset used, walk-forward settings, fold-level metrics, and aggregate out-of-sample metrics.

## Schema fields

- `feature_names`: Ordered list of feature columns required at inference time.
- `schema_version`: Feature schema version.
- `model_version`: Human-readable model label.

Why this matters:
- If runtime features do not match `feature_names`, inference should not be trusted.

## Metadata fields

Top-level keys:

- `generated_at`: Training completion timestamp.
- `dataset_csv`: Source dataset path used for this run.
- `rows`: Number of training rows.
- `target_col`: Binary label column.
- `run_date_col`: Time column used for walk-forward splitting.
- `feature_columns`: Features used in training.
- `walk_forward`: Sliding-window training/validation settings.
- `fold_metrics`: One result per fold.
- `aggregate_oos_metrics`: Metrics over all out-of-sample rows combined.
- `model_path`: Output model path.
- `schema_path`: Output schema path.

### `walk_forward`

- `train_weeks`: Historical weeks per train window.
- `val_weeks`: Future weeks per validation window.
- `step_weeks`: How far to slide windows each fold.
- `folds_used`: Number of valid folds run.

### `fold_metrics` (each fold)

- `fold`: Fold index.
- `train_date_start`, `train_date_end`: Training window bounds.
- `val_date_start`, `val_date_end`: Validation window bounds.
- `train_rows`, `val_rows`: Rows used in that fold.
- `brier`: Probability error metric (lower is better).
- `logloss`: Probability error metric (lower is better).
- `auc`: Ranking quality metric (higher is better).

### `aggregate_oos_metrics`

- `oos_rows`: Number of combined out-of-sample rows.
- `brier`: Combined Brier score.
- `logloss`: Combined log loss.
- `auc`: Combined AUC.

## Interpreting a fold

If a fold has:
- `train_date_start=2024-10-20`
- `train_date_end=2025-01-05`
- `val_date_start=2025-01-12`
- `val_date_end=2025-02-02`

Then:
- The model only learned from dates up to 2025-01-05.
- It was tested on future dates 2025-01-12..2025-02-02.
- This structure is intended to reduce future-data leakage.

## Trust checklist before real-money use

1. Confirm inference features match schema exactly.
2. Confirm fold windows are time-ordered with no overlap leakage.
3. Review worst folds, not only aggregate metrics.
4. Compare model vs heuristic with identical backtest execution assumptions.
5. Store model/schema versions with every trading run.
6. Run in dry mode before any real order placement.

## Repro training command

```bash
PYTHONPATH=src python3 -m kalshi.train_tsa_probability_model \
  --dataset-csv src/data/datasets/tsa_contract_dataset.csv \
  --target-col y_yes_win \
  --run-date-col run_date \
  --train-weeks 12 \
  --val-weeks 4 \
  --step-weeks 2 \
  --out-model src/data/models/tsa_yes_probability_model.joblib
```

Default features (when `--features` is omitted):

- `strike_distance_pct`
- `abs_strike_distance_pct`
- `day_7_trend`
