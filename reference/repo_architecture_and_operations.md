# Repository Architecture And Operations Guide

This document is a practical guide to how this repo is organized, how the TSA system works end-to-end, and how to operate it safely.

## 1) What this repository does

This repository contains:

- shared Kalshi client/auth/order utilities,
- multiple strategy scripts,
- an actively developed TSA trading pipeline with:
  - a passenger forecast step,
  - contract-level probability modeling,
  - backtesting/evaluation tooling,
  - model governance scaffolding.

## 2) Key folders

- `src/kalshi/`: all Python application code.
- `src/data/`:
  - `datasets/`: training/evaluation datasets.
  - `models/`: promoted model artifacts.
  - `models/ablation/`: non-promoted ablation artifacts.
  - `tsa_market_history/`: cached market candles.
- `src/reports/`:
  - `baselines/`: pinned benchmark outputs.
  - `experiments/`: iterative experiments and model comparisons.
  - `archive/`: legacy outputs kept for traceability.
- `reference/`: long-form documentation and process guides.
- `test/`: pytest suite.

## 3) TSA system modules (source of truth)

- Forecast generation:
  - `src/kalshi/create_next_week_prediction.py`
- Live contract probability + pricing selection:
  - `src/kalshi/get_current_tsa_market_prices.py`
- Model feature/inference bundle:
  - `src/kalshi/contract_probability_model.py`
- Model training:
  - `src/kalshi/train_tsa_probability_model.py`
- Feature ablations:
  - `src/kalshi/run_tsa_feature_ablation.py`
- Backtest engine:
  - `src/kalshi/backtest_tsa.py`
- Baseline pipeline runner:
  - `src/kalshi/run_tsa_baseline.py`
- Comparison and sanity analysis:
  - `src/kalshi/analyze_backtest_sanity.py`
  - `src/kalshi/compare_backtests.py`

## 4) Operational rules (important)

- In `prob_source="model"` mode, failures must be hard failures.
  - No silent fallback to heuristic in model mode.
- In `prob_source="heuristic"` mode, heuristics run explicitly.
- Promoted model must always have:
  - `.joblib`
  - `.schema.json`
  - `.metadata.json`
- Use `MODEL_REGISTRY.md` to record promotion state.

## 5) Model governance files

- `MODEL_REGISTRY.md`: promoted model ledger.
- `reference/model_promotion_checklist.md`: release gate checklist.
- `src/kalshi/repo_audit.py`: organization/transparency checks.

Run audit:

```bash
PYTHONPATH=src python3 -m kalshi.repo_audit
```

## 6) Recommended operator workflow

1. Update TSA data.
2. Build or refresh dataset.
3. Train model (default lean-core features unless overridden).
4. Run strict model backtest and heuristic baseline on same window.
5. Compare with `compare_backtests`.
6. If promoting:
   - update `MODEL_REGISTRY.md`,
   - complete checklist in `reference/model_promotion_checklist.md`.

## 7) Reproducibility and transparency practices

- Keep experiment outputs under `src/reports/experiments/...`.
- Keep baseline outputs under `src/reports/baselines/...`.
- Keep root `src/reports/` clean (use subfolders).
- Record the exact command and artifact paths in reports/PR descriptions.
- Avoid undocumented manual file edits for model artifacts.
