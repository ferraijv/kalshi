# TSA Backtest Comparison

- baseline_csv: `/Users/jacobferraiolo/kalshi/src/reports/experiments/tsa_model_compare/heuristic_lean_core_promo/tsa_backtest_20260208_183523.csv`
- candidate_csv: `/Users/jacobferraiolo/kalshi/src/reports/experiments/tsa_model_compare/model_lean_core_promo/tsa_backtest_20260208_183615.csv`

## KPI Delta Table
| metric | baseline | candidate | delta_abs | delta_pct |
| --- | --- | --- | --- | --- |
| avg_edge | 0.113528 | 0.034626 | -0.078903 | -69.500351 |
| brier_mean | 0.087368 | 0.061866 | -0.025502 | -29.188780 |
| ece | 0.070105 | 0.014591 | -0.055514 | -79.187014 |
| edge_pnl_corr | 0.098509 | 0.188167 | 0.089658 | 91.014809 |
| hit_rate | 0.889746 | 0.912105 | 0.022359 | 2.512998 |
| logloss_mean | 0.430326 | 0.198355 | -0.231971 | -53.905952 |
| max_drawdown | 2.500000 | 2.910000 | 0.410000 | 16.400000 |
| pnl_avg | 0.043423 | 0.044749 | 0.001326 | 3.053977 |
| pnl_std | 0.196125 | 0.195826 | -0.000298 | -0.152110 |
| pnl_total | 56.320000 | 58.040000 | 1.720000 | 3.053977 |
| sharpe_like | 0.221407 | 0.228516 | 0.007109 | 3.210972 |
| trades | 1297.000000 | 1297.000000 | 0.000000 | 0.000000 |
