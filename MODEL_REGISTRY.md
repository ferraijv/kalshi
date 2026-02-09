# Model Registry

This file is the canonical list of promoted TSA probability model artifacts used (or previously used) for trading/backtests.

## Status values

- `ACTIVE`: current promoted model.
- `INACTIVE`: previously promoted model kept for rollback/repro.
- `EXPERIMENT`: non-promoted artifacts used for research only.

## Entries

| model_id | status | promoted_at | feature_set | model_path | schema_path | metadata_path | comparison_report |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tsa_yes_probability_model_v1_lean_core_20260208 | ACTIVE | 2026-02-08 | strike_distance_pct,abs_strike_distance_pct,day_7_trend | src/data/models/tsa_yes_probability_model.joblib | src/data/models/tsa_yes_probability_model.schema.json | src/data/models/tsa_yes_probability_model.metadata.json | src/reports/experiments/tsa_model_compare/runs/20260208_1836/comparison.md |

## Promotion Notes

- Never promote a model without:
  - passing test suite,
  - strict `prob_source=model` backtest run,
  - baseline-vs-candidate comparison report.
- If a new model is promoted, append a new row and set the prior active row to `INACTIVE`.
