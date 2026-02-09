# Model Promotion Checklist (TSA)

Use this checklist before changing `ACTIVE` model status in `MODEL_REGISTRY.md`.

## 1) Code and tests

- [ ] `PYTHONPATH=src python3 -m pytest` passes.
- [ ] No silent model->heuristic fallback paths were introduced.
- [ ] `prob_source="model"` still fails fast on inference failures.

## 2) Artifact integrity

- [ ] Model triplet exists:
  - `.joblib`
  - `.schema.json`
  - `.metadata.json`
- [ ] `schema.feature_names` exactly matches `metadata.feature_columns`.
- [ ] Metadata has walk-forward settings and fold metrics.

## 3) Evaluation pack

- [ ] Baseline heuristic backtest produced on the target window.
- [ ] Candidate model backtest produced on the exact same window.
- [ ] Comparison report generated with `kalshi.compare_backtests`.
- [ ] Candidate review includes:
  - `pnl_total`
  - `max_drawdown`
  - `brier_mean`
  - `logloss_mean`
  - `hit_rate`
- [ ] Strict model run confirms:
  - `prob_source_model > 0`
  - `prob_source_heuristic = 0`

## 4) Documentation updates

- [ ] `MODEL_REGISTRY.md` updated (new row + status changes).
- [ ] `README.md` updated if commands/defaults changed.
- [ ] `ROADMAP.md` updated with next risks/follow-ups.

## 5) Sign-off

- Reviewer:
- Date:
- Decision: `PROMOTE` / `DO NOT PROMOTE`
- Notes:
