# TSA Trading Bot Roadmap (Updated 2026-02-09)

Scope: ship a trustworthy TSA trading system where probability modeling, decision logic, and execution are auditable and safe for real money.

## Status Snapshot

### Completed

- Data and backtest hardening:
  - Historical calibration slicing is now point-in-time by `run_date`.
  - Candle cache keys include request window + flags to avoid contamination.
- Model infrastructure:
  - sklearn model bundle + schema + metadata flow is in place.
  - Walk-forward training workflow is implemented.
  - Feature ablation runner is implemented (`run_tsa_feature_ablation.py`).
- Safety behavior:
  - Strict model mode is enforced.
  - In `prob_source="model"`, inference failure raises; no silent heuristic fallback.
- Lean-core model promotion:
  - Default training features now use:
    - `strike_distance_pct`
    - `abs_strike_distance_pct`
    - `day_7_trend`
  - Production artifact retrained and promoted.
- Validation + reporting:
  - A/B backtest comparison tooling is in place.
  - Latest lean-core promotion comparison shows:
    - better `pnl_total` vs heuristic on current test window,
    - much better probability metrics,
    - higher max drawdown (needs mitigation).
- Repo governance scaffolding:
  - `MODEL_REGISTRY.md` added.
  - `reference/model_promotion_checklist.md` added.
  - `kalshi.repo_audit` CLI added for organization/transparency checks.

## Near-Term Priorities (Next 1-2 sessions)

## 1) Decision policy tuning (highest priority)
Goal: convert improved probabilities into better risk-adjusted PnL.

- Add configurable entry gating:
  - minimum edge threshold,
  - optional no-trade zone around 0.5,
  - optional price/spread filters.
- Run threshold sweeps on fixed windows.
- Select policy by gates:
  - improve/hold `pnl_total`,
  - reduce max drawdown,
  - preserve calibration quality.

## 2) Drawdown control and risk caps
Goal: make live behavior safer before further capital exposure.

- Add per-trade and per-event position caps.
- Add daily max-loss stop behavior for live loop.
- Add backtest reporting for drawdown episodes and tail loss concentration.

## 3) Dataset and feature expansion (incremental)
Goal: evaluate whether richer point-in-time features add real value.

- Add candidate feature families one at a time:
  - market microstructure (`yes_ask`, `no_ask`, spread, mid),
  - liquidity proxies,
  - time-to-settlement context.
- Re-run ablation + strict A/B after each addition.
- Promote only if both OOS metrics and backtest outcomes improve.

## Mid-Term Priorities

## 4) Calibration layer
Goal: improve decision-grade probability reliability.

- Add Platt or isotonic calibration with proper fold isolation.
- Track rolling calibration diagnostics (ECE + bin tables) in reports.

## 5) Execution-realistic simulation
Goal: reduce research/live mismatch.

- Model partial fills, missed fills, and order timeout behavior.
- Add execution assumptions as config and include in comparison metadata.

## 6) Live pipeline auditability
Goal: deterministic, inspectable operations.

- Formal run manifest per live run:
  - code version,
  - model artifact/schema version,
  - config hash,
  - key input timestamps.
- Keep dry-run and live modes behaviorally aligned except order submission.

## Operating Rules

- Model mode must remain fail-fast.
- Any model promotion requires:
  - full pytest pass,
  - strict model-vs-heuristic comparison report,
  - documented artifact versions in `src/data/models/`.
