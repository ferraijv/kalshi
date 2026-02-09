# Kalshi Trading Framework

This repository contains multiple Kalshi strategy scripts and shared infrastructure, with an active focus on the TSA weekly market modeling pipeline.

## Current State

- Core strategy/runtime code lives in `src/kalshi/`.
- TSA probability modeling is active and now runs in strict mode:
  - `prob_source="model"` fails fast if model inference cannot run.
  - No silent model->heuristic fallback.
- Current production TSA model uses lean-core features:
  - `strike_distance_pct`
  - `abs_strike_distance_pct`
  - `day_7_trend`
- Latest promoted TSA model artifacts:
  - `src/data/models/tsa_yes_probability_model.joblib`
  - `src/data/models/tsa_yes_probability_model.schema.json`
  - `src/data/models/tsa_yes_probability_model.metadata.json`

## Repository Layout

- `src/kalshi/shared.py`: auth/login helpers, shared trading utilities, IDs, notifications.
- `src/kalshi/clients.py`: Kalshi API client wrappers.
- `src/kalshi/tsa_trading_bot.py`: TSA live workflow entrypoint.
- `src/kalshi/create_next_week_prediction.py`: TSA passenger forecast generation.
- `src/kalshi/get_current_tsa_market_prices.py`: contract probability generation for live use.
- `src/kalshi/backtest_tsa.py`: TSA backtest engine.
- `src/kalshi/train_tsa_probability_model.py`: model training CLI.
- `src/kalshi/run_tsa_feature_ablation.py`: feature-set train/backtest ablation runner.
- `src/kalshi/analyze_backtest_sanity.py`: sanity metric report generation.
- `src/kalshi/compare_backtests.py`: baseline/candidate comparison report generation.
- `src/kalshi/fetch_tsa_history.py`: TSA candle history fetch + cache.
- `src/data/`: datasets, model artifacts, caches.
- `src/reports/`: generated backtests, comparisons, ablations.
- `reference/`: docs and guides.
- `test/`: pytest suite.

## Environment

- Python: `3.9.x`
- Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

- Run commands from repo root with `PYTHONPATH=src`.

## Testing

Run full test suite:

```bash
PYTHONPATH=src python3 -m pytest
```

Run repo organization/transparency audit:

```bash
PYTHONPATH=src python3 -m kalshi.repo_audit
```

## TSA Workflow

### 1) Refresh TSA source data

```bash
PYTHONPATH=src python3 -m kalshi.get_recent_tsa_data
```

### 2) (Optional) Rebuild point-in-time contract dataset

```bash
PYTHONPATH=src python3 -m kalshi.build_tsa_contract_dataset
```

### 3) Train TSA probability model (lean-core defaults)

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

### 4) Run heuristic baseline backtest

```bash
PYTHONPATH=src python3 -m kalshi.backtest_tsa \
  --start 2024-10-27 \
  --end 2026-02-01 \
  --interval 1440 \
  --cache src/data/tsa_market_history \
  --report-dir src/reports/experiments/tsa_model_compare/heuristic \
  --prob-source heuristic
```

### 5) Run strict model backtest

```bash
PYTHONPATH=src python3 -m kalshi.backtest_tsa \
  --start 2024-10-27 \
  --end 2026-02-01 \
  --interval 1440 \
  --cache src/data/tsa_market_history \
  --report-dir src/reports/experiments/tsa_model_compare/model \
  --prob-source model \
  --model-bundle src/data/models/tsa_yes_probability_model.joblib
```

### 6) Compare baseline vs model

```bash
PYTHONPATH=src python3 -m kalshi.compare_backtests \
  --baseline <baseline_csv> \
  --candidate <candidate_csv> \
  --out <comparison_md>
```

### 7) Run feature ablations

```bash
PYTHONPATH=src python3 -m kalshi.run_tsa_feature_ablation \
  --start 2024-10-27 \
  --end 2026-02-01 \
  --report-dir src/reports/experiments/tsa_feature_ablation \
  --model-dir src/data/models/ablation \
  --cache src/data/tsa_market_history
```

## Backtest Output Notes

- `backtest_tsa` CSV rows include `prob_source_used` to audit which probability path produced each trade.
- Markdown summary includes:
  - `prob_source_model`
  - `prob_source_heuristic`

In strict model runs, `prob_source_heuristic` should be `0`.

## Live Trading Safety Notes

- In model mode, inference failures are fatal by design.
- Validate schema/metadata before using a new model artifact.
- Do not run live scripts without valid credentials and a reviewed risk process.

## References

- Kalshi endpoint/contracts reference: `reference/kalshi_docs`
- TSA model artifact guide:
  - `reference/tsa_yes_probability_model_artifacts.md`
  - `src/data/models/tsa_yes_probability_model.README.md`
- Comprehensive repo architecture and operations:
  - `reference/repo_architecture_and_operations.md`
- Comprehensive model theory + implementation:
  - `reference/tsa_models_theory_and_implementation.md`
- Promotion and governance:
  - `MODEL_REGISTRY.md`
  - `reference/model_promotion_checklist.md`
- TSA metrics guide: `reference/tsa_model_metrics_guide.md`
- Delivery plan: `ROADMAP.md`
