# TSA Backtest Sanity Report

- source_csv: `/Users/jacobferraiolo/kalshi/src/reports/tsa_backtest_20260207_143826.csv`
- generated_at: 2026-02-07T17:17:44
- trades: 189
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
- [PASS] logloss_abs_delta: max_delta=7.37188088351e-14, rows_over_tolerance=0
- [PASS] edge_abs_delta: max_delta=2.06432093641e-16, rows_over_tolerance=0

## Key Metrics
- pnl_total: 7.040000
- pnl_avg: 0.037249
- pnl_std: 0.200526
- sharpe_like: 0.185755
- max_drawdown: 2.500000
- hit_rate: 0.851852
- avg_edge: 0.170046
- edge_pnl_corr: 0.076147
- brier_mean: 0.139498
- logloss_mean: 1.562131
- ece: 0.137159
- pnl_avg_95pct_bootstrap_ci: [0.007036, 0.065901]

## Edge Diagnostics
- n_edge_positive: 183
- n_edge_non_positive: 6
- corr_edge_pnl: 0.076147
- mean_pnl_edge_positive: 0.036120
- mean_pnl_edge_non_positive: 0.071667
- hit_rate_edge_positive: 0.846995
- hit_rate_edge_non_positive: 1.000000

## By Side
| side | trades | hit_rate | avg_prob | avg_fill_price | avg_edge | avg_pnl | pnl_total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| no | 81 | 0.901235 | 0.975671 | 0.153889 | 0.129560 | 0.055123 | 4.465000 |
| yes | 108 | 0.814815 | 0.991383 | 0.790972 | 0.200410 | 0.023843 | 2.575000 |

## Calibration (confidence bins)
| bin | trades | mean_confidence | hit_rate | avg_pnl | calibration_gap |
| --- | --- | --- | --- | --- | --- |
| (-0.001, 0.1] | 0 | nan | nan | nan | nan |
| (0.1, 0.2] | 0 | nan | nan | nan | nan |
| (0.2, 0.3] | 0 | nan | nan | nan | nan |
| (0.3, 0.4] | 0 | nan | nan | nan | nan |
| (0.4, 0.5] | 0 | nan | nan | nan | nan |
| (0.5, 0.6] | 1 | 0.587792 | 1.000000 | 0.220000 | 0.412208 |
| (0.6, 0.7] | 2 | 0.694800 | 0.500000 | -0.120000 | -0.194800 |
| (0.7, 0.8] | 2 | 0.742653 | 0.500000 | -0.172500 | -0.242653 |
| (0.8, 0.9] | 3 | 0.850791 | 0.666667 | 0.061667 | -0.184125 |
| (0.9, 1.0] | 181 | 0.994937 | 0.861878 | 0.039890 | -0.133059 |
