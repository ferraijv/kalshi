# TSA Backtest Comparison

- baseline_csv: `/Users/jacobferraiolo/kalshi/src/reports/experiments/tsa_model_compare/heuristic_strict/tsa_backtest_20260208_163928.csv`
- candidate_csv: `/Users/jacobferraiolo/kalshi/src/reports/experiments/tsa_model_compare/model_strict/tsa_backtest_20260208_164003.csv`

## KPI Delta Table
| metric | baseline | candidate | delta_abs | delta_pct |
| --- | --- | --- | --- | --- |
| avg_edge | 0.113561 | 0.036090 | -0.077470 | -68.219229 |
| brier_mean | 0.087390 | 0.057860 | -0.029531 | -33.791765 |
| ece | 0.070137 | 0.010631 | -0.059506 | -84.842505 |
| edge_pnl_corr | 0.098439 | 0.179582 | 0.081143 | 82.429914 |
| hit_rate | 0.889746 | 0.920586 | 0.030840 | 3.466205 |
| logloss_mean | 0.430644 | 0.183957 | -0.246687 | -57.283183 |
| max_drawdown | 2.500000 | 2.640000 | 0.140000 | 5.600000 |
| pnl_avg | 0.043423 | 0.042167 | -0.001257 | -2.894176 |
| pnl_std | 0.196125 | 0.196399 | 0.000274 | 0.139724 |
| pnl_total | 56.320000 | 54.690000 | -1.630000 | -2.894176 |
| sharpe_like | 0.221407 | 0.214699 | -0.006708 | -3.029667 |
| trades | 1297.000000 | 1297.000000 | 0.000000 | 0.000000 |
