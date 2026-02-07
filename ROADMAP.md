# TSA Trading Bot Roadmap (2026)

Scope: Improve TSA prediction model, pricing, and execution to raise EV while reducing operational risk. Durations are rough; adjust as capacity/feedback comes in.

## Phase 1 – Hardening & Safety (Week 1–2)
- Data integrity: add retries/backoff + checksum for TSA fetch; validate column schema and stale-data guard (done); write `.gitignore` for data cache.
- Run hygiene: wire a `--dry-run` flag through TSA pipeline; stop if prediction/expiry mismatch or spread too wide; fail fast on missing secrets.
- Pricing sanity: use mid-price when available, require min edge (prob - price) > fees + buffer; cap spread width; skip tiny size markets.
- Risk controls: per-trade max $ risk, per-day cap, circuit breaker on recent drawdown/API errors.
- CI habit: keep `PYTHONPATH=src python3 -m pytest -q` as default post-change step.

## Phase 2 – Calibration & Backtesting (Week 3–4)
- Build rolling backtest for last 12–24 months using current rule model; log PnL, Brier, log-loss, calibration curves.
- Probability calibration: apply isotonic or Platt scaling to raw likelihoods vs outcomes; persist calibrators per vintage.
- Threshold tuning: grid-search EV thresholds and size multipliers using historical spreads/fees; choose conservative defaults.
- Reporting: nightly/weekly HTML report with metrics and best thresholds; email/Slack stub.

## Phase 3 – Feature & Model Upgrade (Week 4–6)
- Features: holiday flags (federal + school breaks), seasonality (week-of-year, month), 14/28-day trends, days-to-holiday, weather optional.
- Model: start with gradient boosting or Prophet/ARIMA; output predictive distribution (mean, p10/p90) for each settlement.
- Validation: time-series CV; compare to baseline rule model; keep calibration step post-model.

## Phase 4 – Execution Quality (Week 6–8)
- Edge-aware sizing: fractional Kelly or capped fixed-dollar sizing based on calibrated edge and variance; degrade size when sample count small.
- Order tactics: post-only at edge, reprice toward mid with limited chase, cancel-before-close rules; skip when spread/size thin.
- Slippage model: simulate fills using historical spreads/queue depth; bake expected fill probability into EV.

## Phase 5 – Monitoring & Ops (Ongoing)
- Telemetry: structured logs for inputs, probs, prices, orders, fills; daily PnL attribution and hit-rate dashboards.
- Alerts: stale data, API errors, calibration drift, drawdown breach.
- Artifact versioning: store data snapshot + model/calibrator hash per run; include in emails.

## Fastest Wins to tackle next
1) Mid-price + spread gate + EV buffer before order placement (Phase 1).  
2) Per-trade/per-day risk caps and dry-run flag plumbing (Phase 1).  
3) Rolling backtest + calibration curves (Phase 2 starter).  
4) Threshold tuning using historical spreads/fees (Phase 2).  

Ownership: default to on-call agent unless a maintainer assigns; keep tasks bite-sized and PR-scoped. 
