# TSA Model Metrics Guide (Plain English)

This guide explains the metrics you see in:

- `src/data/models/tsa_yes_probability_model.metadata.json`
- model training output printed by `train_tsa_probability_model`

## What the model is predicting

The model outputs a probability:

- `P(YES wins)` for each contract

So every metric below evaluates how good those probabilities are.

## Quick glossary

### `AUC` (Area Under ROC Curve)
- What it measures:
  - How well the model ranks winners above losers.
- Scale:
  - `0.5` = random
  - `1.0` = perfect ranking
- Direction:
  - Higher is better.
- Important:
  - AUC checks ranking quality, not whether probabilities are well calibrated.

### `Brier` (Brier score)
- What it measures:
  - Average squared error of probabilities.
- Formula idea:
  - Compare predicted probability to actual outcome (`0` or `1`) and square the difference.
- Scale:
  - `0` is best.
  - Bigger means worse probability quality.
- Direction:
  - Lower is better.

### `Logloss` (cross-entropy loss)
- What it measures:
  - How much the model is penalized for being confidently wrong.
- Behavior:
  - Small if model gives high probability to true outcomes.
  - Large if model gives high probability to false outcomes.
- Scale:
  - `0` is best.
  - Unbounded above.
- Direction:
  - Lower is better.

### `oos_rows`
- Meaning:
  - Number of out-of-sample rows used for aggregate metrics.
- Why it matters:
  - More rows usually means more stable metrics.

## What “folds” mean

Each fold is one walk-forward test:

1. Train on older dates.
2. Validate on the next future dates.
3. Slide forward and repeat.

Fold date fields:

- `train_date_start`, `train_date_end`
- `val_date_start`, `val_date_end`

This is designed to mimic real trading conditions and reduce future-data leakage.

## How to read one fold

Example:
- `AUC = 0.98`, `Brier = 0.06`, `Logloss = 0.20`

Interpretation:
- Ranking is strong.
- Probabilities are reasonably accurate.
- No major confidence mistakes.

Bad-fold example:
- `AUC = 0.66`, `Brier = 0.36`, `Logloss = 2.03`

Interpretation:
- Model has weak ranking.
- Probabilities are poor.
- It made very confident wrong calls (high logloss).

## Why metrics can disagree

This is normal:

- You can have high AUC but bad Brier/logloss.
- That means:
  - ordering is good, but probability magnitudes are off.

For trading decisions, probability quality matters, so prioritize:

1. `Logloss`
2. `Brier`
3. `AUC`

## Practical decision checklist

Before promoting a model:

1. Check aggregate metrics are better than baseline.
2. Check worst folds, not just average.
3. Investigate time windows where metrics collapse.
4. Confirm backtest PnL and risk metrics also improve.
5. Keep heuristic fallback available until stability is proven.

## Simple mental model

- `AUC`: “Did we rank likely winners ahead of likely losers?”
- `Brier`: “Were our probabilities numerically close to reality?”
- `Logloss`: “Did we get punished for being confidently wrong?”

Use all three together, not one alone.

