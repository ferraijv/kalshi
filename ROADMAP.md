# TSA Trading Bot Roadmap (Updated 2026-02-08)

Scope: Improve TSA forecasting, contract pricing, and execution to maximize risk-adjusted profit while keeping operational risk controlled.

## Status Snapshot
### Completed recently
- Backtest leakage fix: calibration history is now time-sliced to each event `run_date` in `/Users/jacobferraiolo/kalshi/src/kalshi/backtest_tsa.py`.
- Candle cache contamination fix: cache key now includes request window (`start_ts`, `end_ts`) and `include_latest_before_start` in `/Users/jacobferraiolo/kalshi/src/kalshi/fetch_tsa_history.py`.
- Phase 0 baseline/measurement framework:
  - Canonical KPI set + metadata JSON output in `/Users/jacobferraiolo/kalshi/src/kalshi/analyze_backtest_sanity.py`.
  - Baseline-vs-candidate comparison CLI in `/Users/jacobferraiolo/kalshi/src/kalshi/compare_backtests.py`.
  - Baseline run config in `/Users/jacobferraiolo/kalshi/src/kalshi/configs/tsa_backtest_baseline.json`.
- README updated to document the measurement workflow and commands.

### In progress focus
- Move from heuristic probability rules to calibrated, walk-forward probabilistic pricing.
- Align backtest execution assumptions with actual live order behavior.

## Phase 0 – Baseline And Measurement (Complete)
Goal: establish trusted benchmark metrics before strategy changes.
- Define canonical KPIs: `pnl_total`, `pnl_avg`, `pnl_std`, `sharpe_like`, `max_drawdown`, `hit_rate`, `avg_edge`, `edge_pnl_corr`, `brier_mean`, `logloss_mean`, `ece`.
- Generate reproducibility metadata for each sanity run (CSV hash, git commit, command, python version).
- Add baseline/candidate KPI comparison tooling.
- Deliverables:
  - `analyze_backtest_sanity` markdown + JSON output.
  - `compare_backtests` markdown delta report.
  - Baseline config in `configs/`.

## Phase 1 – Data Layer Hardening (Week 1)
Goal: ensure point-in-time correctness and experiment reproducibility.
- Build a single dataset generator for model/backtest inputs with explicit as-of timestamps.
- Add strict leakage tests for every derived feature used in probability estimation.
- Version training/backtest datasets with checksums and generation metadata.
- Add baseline runner script that reads `tsa_backtest_baseline.json` and runs:
  - backtest
  - sanity analysis
  - metadata + comparison hooks

## Phase 2 – Probabilistic Pricing Model (Week 2–3)
Goal: replace empirical CDF heuristics with direct contract probability modeling.
- Train per-contract probability model `P(win | features, strike, run_date)` using walk-forward splits.
- Start with logistic baseline; graduate to boosted trees if out-of-sample gains are consistent.
- Keep strict train/validation windows with no future data crossover.
- Persist model artifacts and feature schema version.

## Phase 3 – Calibration Layer (Week 3)
Goal: make predicted probabilities decision-grade.
- Add isotonic/Platt calibration on validation windows only.
- Track calibration by confidence bins and rolling expected calibration error.
- Add guardrails for extreme probabilities (clipping/floor/ceiling policy).

## Phase 4 – Decision Engine (Week 4)
Goal: trade only when expected value survives execution costs and risk limits.
- Replace fixed `0.75 * true_value` pricing with EV-driven order logic.
- Compute net EV after spread, fees, slippage/fill haircut.
- Add position sizing using capped fractional Kelly (or capped fixed-risk fallback).
- Enforce per-trade, per-event, and per-day risk caps.

## Phase 5 – Execution-Realistic Backtesting (Week 5)
Goal: make research metrics match deployable live behavior.
- Simulate limit-order lifecycle (fill uncertainty, partial fills, unfilled cancels).
- Parameterize re-quote logic, timeout logic, and liquidity filters.
- Report realized-vs-theoretical edge decomposition.
- Add acceptance gates comparing strategy deltas against baseline KPIs.

## Phase 6 – Live Pipeline Refactor (Week 6)
Goal: make production flow deterministic and auditable.
- Modularize TSA run sequence: data -> predict -> calibrate -> decide -> execute -> report.
- Add dry-run mode and idempotent order keys.
- Ensure `run_date` semantics are consistent across scheduling and order placement.

## Phase 7 – Monitoring And Rollout (Week 7+)
Goal: safe production iteration with clear promotion criteria.
- Add telemetry for inputs, probabilities, quotes, orders, fills, and PnL attribution.
- Alerting: stale data, calibration drift, fill deterioration, drawdown breach.
- Rollout protocol: shadow mode -> paper mode -> gradual capital ramp with hard stop rules.

## Immediate Next Actions
1. Implement baseline runner script from `tsa_backtest_baseline.json`.
2. Build point-in-time feature dataset generator for walk-forward model training.
3. Ship logistic baseline + calibration and compare against current heuristic via `compare_backtests`.
4. Add EV/risk decision engine in dry-run mode before touching live order logic.
