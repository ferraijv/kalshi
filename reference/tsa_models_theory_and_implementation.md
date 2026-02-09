# TSA Models: Theory And Implementation

This document explains each model in the TSA pipeline from two perspectives:

- high-level theory (what problem it solves and why),
- technical implementation (how it is coded in this repository).

## 1) System objective

For each TSA contract strike, estimate:

- `P(YES wins | information available at run_date)`

where `YES` means the settled TSA passenger level is at or above the contract strike.

The final trading step then maps this probability to a side (`yes`/`no`) and compares against market price.

---

## 2) Model A: TSA Passenger Forecast Model

### High-level theory

This is a time-series heuristic model for weekly TSA passenger level forecasting.

Core idea:

- start from last year’s comparable traffic baseline (same ISO week/day alignment),
- scale it using recent trend multipliers.

This gives a forecast for next Sunday’s passenger level, which is then transformed into contract-level features.

### Technical implementation

File:

- `src/kalshi/create_next_week_prediction.py`

Main stages:

1. `lag_passengers()`
   - loads TSA raw CSV (`src/data/tsa_data.csv`),
   - aligns prior-year comparable day,
   - computes:
     - `passengers_7_day_moving_average`
     - `passengers_7_day_moving_average_previous_year`.
2. `get_recent_trend()`
   - computes:
     - `current_trend_1_day = passengers / previous_year`
     - `current_trend = 7d_ma / previous_year_7d_ma`
   - computes lagged trend and prediction.
3. `get_prediction()`
   - retrieves last-year reference value for target Sunday,
   - builds weighted trend adjustment:
     - `yoy_adjustment = 0.8 * day_7_trend + 0.2 * day_1_trend`,
   - outputs prediction payload containing:
     - `prediction`
     - `day_1_trend`
     - `day_7_trend`
     - `yoy_adjustment`
     - `last_year_passengers`.

Important guardrails:

- freshness checks via `ensure_data_fresh`,
- hard errors when prior-year reference or trend values are missing/NaN.

---

## 3) Model B: Heuristic Contract Likelihood Model (legacy baseline)

### High-level theory

This model prices contracts using empirical distribution of historical forecast errors.

Idea:

- compare current strike-distance (`prediction / strike - 1`) to historical percent errors,
- estimate probability as empirical CDF percentile.

This is non-parametric and simple, but can be noisy and less calibrated than supervised classification.

### Technical implementation

File:

- `src/kalshi/get_current_tsa_market_prices.py`

Key functions:

- `get_likelihood_of_yes(prediction, floor_strike, historical_data)`
- `get_likelihood_of_no(prediction, floor_strike, historical_data)`
- `_load_historical_likelihood_data()` from `lagged_tsa_data.csv`.

Usage mode:

- only when `prob_source="heuristic"`.

---

## 4) Model C: Contract Probability Logistic Regression (current promoted model family)

### High-level theory

This is a supervised binary classifier that directly predicts contract settlement probability.

Target:

- `y_yes_win` (1 if `actual_passengers >= floor_strike`, else 0).

Compared to Model B, this learns a parametric probability mapping from features to win likelihood with explicit train/validation splits.

### Technical implementation

Files:

- `src/kalshi/train_tsa_probability_model.py`
- `src/kalshi/contract_probability_model.py`
- runtime callers:
  - `src/kalshi/get_current_tsa_market_prices.py`
  - `src/kalshi/backtest_tsa.py`

Training pipeline:

- median imputation (`SimpleImputer`),
- standardization (`StandardScaler`),
- binary logistic regression (`LogisticRegression`, `lbfgs`, `l2`).

Validation protocol:

- walk-forward splits by `run_date`,
- no future leakage across train/validation windows.

Artifacts:

- model: `.joblib`
- schema: `.schema.json` (`feature_names`, versions)
- metadata: `.metadata.json` (fold metrics + aggregate OOS metrics)

### Current promoted default feature set (`lean_core`)

- `strike_distance_pct`
- `abs_strike_distance_pct`
- `day_7_trend`

Rationale from ablation:

- best combined OOS + backtest outcome among tested sets in current window.

---

## 5) Model variants from ablation (what was tested)

Ablation runner:

- `src/kalshi/run_tsa_feature_ablation.py`

Artifacts:

- `src/data/models/ablation/*.joblib|*.schema.json|*.metadata.json`
- report: `src/reports/experiments/tsa_feature_ablation/tsa_feature_ablation_20260208_164726.md`

Variants tested:

1. `full`
   - all candidate engineered features.
2. `lean_core`
   - distance + weekly trend.
3. `lean_plus_strike_level`
   - lean_core + `floor_strike_millions`.
4. `lean_plus_last_year`
   - lean_core + `last_year_passengers`.
5. `no_composite_yoy`
   - removes composite `yoy_adjustment`, keeps component trends.
6. `without_days_until_sunday`
   - drops `days_until_sunday`.

Observed conclusions (current run):

- `lean_core` ranked best on OOS Brier/logloss/AUC and best backtest `pnl_total`.
- `days_until_sunday` had effectively no incremental value in this setup.

---

## 6) Probability-to-trade mapping (decision layer, not model training)

After `prob_yes` is produced:

- `map_yes_probability_to_side()` picks:
  - `yes` if `prob_yes >= 0.5`
  - `no` otherwise.

Then:

- side probability (`prob`) is compared against implied contract price to compute edge.
- Backtest records:
  - `pnl`, `brier`, `logloss`, `edge`, and `prob_source_used`.

This decision policy is currently simple and should be tuned separately from probability modeling.

---

## 7) Safety behavior and failure policy

Strict mode behavior:

- if `prob_source="model"` and model inference fails, code raises `RuntimeError`.
- no silent heuristic fallback in model mode.

This is implemented in:

- `src/kalshi/get_current_tsa_market_prices.py`
- `src/kalshi/backtest_tsa.py`

---

## 8) Known limitations and next modeling work

Current limitations:

- feature set is intentionally lean and may miss market microstructure signals.
- improved calibration does not automatically maximize PnL; decision policy matters.

Next modeling priorities:

1. decision threshold tuning (edge/no-trade band),
2. drawdown-aware constraints,
3. incremental feature families (price/spread/liquidity/time-to-settlement),
4. calibration layer (Platt/isotonic with strict fold isolation).

---

## 9) Where to check model truth in this repo

- promoted model status: `MODEL_REGISTRY.md`
- artifact interpretation:
  - `src/data/models/tsa_yes_probability_model.README.md`
  - `reference/tsa_yes_probability_model_artifacts.md`
- promotion gate:
  - `reference/model_promotion_checklist.md`
