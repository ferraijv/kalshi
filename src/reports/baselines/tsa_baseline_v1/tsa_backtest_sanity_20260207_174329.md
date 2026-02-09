# TSA Backtest Sanity Report

- source_csv: `src/reports/baselines/tsa_baseline_v1/tsa_backtest_20260207_174329.csv`
- generated_at: 2026-02-07T17:46:26
- trades: 1297
- checks_passed: 10/10

## Invariant Checks
- [PASS] required_columns: missing=none
- [PASS] prob_in_[0,1]: below=0, above=0, bounds=[0.0, 1.0]
- [PASS] fill_price_in_[0,1]: below=0, above=0, bounds=[0.0, 1.0]
- [PASS] side_is_yes_or_no: invalid_rows=0
- [PASS] outcome_is_binary: invalid_rows=0
- [PASS] no_duplicate_market_date_rows: duplicates=0
- [PASS] pnl_abs_delta: max_delta=9.71445146547e-17, rows_over_tolerance=0
- [PASS] brier_abs_delta: max_delta=3.33066907388e-16, rows_over_tolerance=0
- [PASS] logloss_abs_delta: max_delta=2.04281036531e-14, rows_over_tolerance=0
- [PASS] edge_abs_delta: max_delta=2.22044604925e-16, rows_over_tolerance=0

## Key Metrics
- pnl_total: 56.410000
- pnl_avg: 0.043493
- pnl_std: 0.196109
- sharpe_like: 0.221778
- max_drawdown: 2.500000
- hit_rate: 0.892059
- avg_edge: 0.133067
- edge_pnl_corr: 0.078005
- brier_mean: 0.096063
- logloss_mean: 0.871953
- ece: 0.090787
- pnl_avg_95pct_bootstrap_ci: [0.032521, 0.054063]

## Edge Diagnostics
- n_edge_positive: 1252
- n_edge_non_positive: 45
- corr_edge_pnl: 0.078005
- mean_pnl_edge_positive: 0.043423
- mean_pnl_edge_non_positive: 0.045444
- hit_rate_edge_positive: 0.888978
- hit_rate_edge_non_positive: 0.977778

## By Side
| side | trades | hit_rate | avg_prob | avg_fill_price | avg_edge | avg_pnl | pnl_total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| no | 458 | 0.879913 | 0.970890 | 0.148046 | 0.118936 | 0.027959 | 12.805000 |
| yes | 839 | 0.898689 | 0.987497 | 0.846716 | 0.140780 | 0.051973 | 43.605000 |

## Calibration (confidence bins)
| bin | trades | mean_confidence | hit_rate | avg_pnl | calibration_gap |
| --- | --- | --- | --- | --- | --- |
| (-0.001, 0.1] | 0 | nan | nan | nan | nan |
| (0.1, 0.2] | 0 | nan | nan | nan | nan |
| (0.2, 0.3] | 0 | nan | nan | nan | nan |
| (0.3, 0.4] | 0 | nan | nan | nan | nan |
| (0.4, 0.5] | 0 | nan | nan | nan | nan |
| (0.5, 0.6] | 11 | 0.564845 | 0.636364 | 0.039091 | 0.071519 |
| (0.6, 0.7] | 16 | 0.655125 | 0.500000 | 0.008125 | -0.155125 |
| (0.7, 0.8] | 13 | 0.749840 | 0.307692 | -0.089231 | -0.442148 |
| (0.8, 0.9] | 35 | 0.853027 | 0.542857 | 0.011286 | -0.310170 |
| (0.9, 1.0] | 1222 | 0.995809 | 0.915712 | 0.046330 | -0.080097 |
