# TSA Feature Ablation

- generated_at: `20260208_164726`
- dataset_csv: `/Users/jacobferraiolo/kalshi/src/data/datasets/tsa_contract_dataset.csv`
- backtest_window: `2024-10-27 -> 2026-02-01`
- walk_forward: `train_weeks=12, val_weeks=4, step_weeks=2`
- backtest_ran: `True`

## Results

| name | num_features | oos_brier | oos_logloss | oos_auc | backtest_pnl_total | backtest_pnl_avg | backtest_hit_rate_proxy | backtest_brier | backtest_logloss | features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lean_core | 3 | 0.07002026840115998 | 0.23989203694470074 | 0.9617953651322403 | 58.04000000000002 | 0.04474942174248267 | 0.9121048573631457 | 0.06186616698325305 | 0.19835464501272834 | strike_distance_pct,abs_strike_distance_pct,day_7_trend |
| no_composite_yoy | 6 | 0.09023104927689261 | 0.3424358837435568 | 0.9364950368051767 | 54.69000000000002 | 0.04216653816499616 | 0.920585967617579 | 0.05785625307109174 | 0.1839515519199124 | floor_strike_millions,strike_distance_pct,abs_strike_distance_pct,day_1_trend,day_7_trend,last_year_passengers |
| full | 8 | 0.09068092198526233 | 0.3436600450101249 | 0.9362968919009467 | 54.69000000000002 | 0.04216653816499616 | 0.920585967617579 | 0.057859689673165064 | 0.1839574624638299 | floor_strike_millions,strike_distance_pct,abs_strike_distance_pct,days_until_sunday,day_1_trend,day_7_trend,yoy_adjustment,last_year_passengers |
| without_days_until_sunday | 7 | 0.09068092198526245 | 0.3436600450101173 | 0.9362968919009467 | 54.69000000000002 | 0.04216653816499616 | 0.920585967617579 | 0.057859689673165064 | 0.1839574624638299 | floor_strike_millions,strike_distance_pct,abs_strike_distance_pct,day_1_trend,day_7_trend,yoy_adjustment,last_year_passengers |
| lean_plus_strike_level | 4 | 0.08566771085272051 | 0.28906812844164115 | 0.9465583091634839 | 53.74000000000002 | 0.04143407864302238 | 0.9198149575944488 | 0.058896486756473666 | 0.18788426793188343 | strike_distance_pct,abs_strike_distance_pct,day_7_trend,floor_strike_millions |
| lean_plus_last_year | 4 | 0.08783704677129335 | 0.3020478469822297 | 0.9406579942375249 | 52.54000000000002 | 0.040508866615266016 | 0.9136468774094063 | 0.059488249844809625 | 0.19093139812786833 | strike_distance_pct,abs_strike_distance_pct,day_7_trend,last_year_passengers |

## Variant Name Lookup

| name | meaning |
| --- | --- |
| lean_core | Minimal core signal set used for simple/robust baseline behavior. |
| no_composite_yoy | Drops `yoy_adjustment` composite and keeps separate trend inputs. |
| full | All currently engineered features. |
| without_days_until_sunday | `full` set without `days_until_sunday`. |
| lean_plus_strike_level | `lean_core` plus raw strike level. |
| lean_plus_last_year | `lean_core` plus last-year passenger level. |

## Feature Name Lookup

| feature | meaning |
| --- | --- |
| floor_strike_millions | Contract strike (floor) converted to millions of passengers. |
| strike_distance_pct | `(prediction - strike) / strike`. Positive means forecast is above strike. |
| abs_strike_distance_pct | Absolute value of `strike_distance_pct`; distance from strike regardless of direction. |
| days_until_sunday | Calendar days from `run_date` to the Sunday settlement date. |
| day_1_trend | Near-term trend from most recent daily movement in TSA passengers. |
| day_7_trend | Week-over-week trend signal from recent 7-day movement. |
| yoy_adjustment | Composite trend adjustment blending `day_7_trend` and `day_1_trend`. |
| last_year_passengers | TSA passenger level from the comparable date last year. |
