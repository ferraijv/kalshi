# Model Executive Summary

- generated_at: `2026-02-08 21:51:53`

## Decision

- status: `GO WITH RISK REVIEW`
- rationale: Candidate improves core KPIs but increases drawdown; risk sign-off required.

## Promoted Model

- model_id: `tsa_yes_probability_model_v1_lean_core_20260208`
- promoted_at: `2026-02-08`
- feature_set: `strike_distance_pct,abs_strike_distance_pct,day_7_trend`
- model_path: `src/data/models/tsa_yes_probability_model.joblib`

## Baseline vs Candidate (Latest Run)

- run_id: `20260208_1836`
- comparison_report: `/Users/jacobferraiolo/kalshi/src/reports/experiments/tsa_model_compare/runs/20260208_1836/comparison.md`

| metric | baseline | candidate | delta_abs |
| --- | --- | --- | --- |
| pnl_total | 56.320000 | 58.040000 | 1.720000 |
| brier_mean | 0.087368 | 0.061866 | -0.025502 |
| logloss_mean | 0.430326 | 0.198355 | -0.231971 |
| ece | 0.070105 | 0.014591 | -0.055514 |
| max_drawdown | 2.500000 | 2.910000 | 0.410000 |
| sharpe_like | 0.221407 | 0.228516 | 0.007109 |

## Best Ablation Variant (Latest Report)

- report: `/Users/jacobferraiolo/kalshi/src/reports/experiments/tsa_feature_ablation/tsa_feature_ablation_20260208_164726.md`
- variant: `lean_core`
- features: `strike_distance_pct,abs_strike_distance_pct,day_7_trend`
- oos_brier: `0.07002026840115998`
- oos_logloss: `0.23989203694470074`
- oos_auc: `0.9617953651322403`
- backtest_pnl_total: `58.04000000000002`
