# AGENTS

Guidance for assistants working in this repo.

Note: Make sure to update this file as you learn. You should update this file regularly to improve your performance.

- **Project overview**: Kalshi trading framework with scripts under `src/kalshi/` and tests in `test/`.
- **Python version**: 3.9.x (current venv); dependencies in `requirements.txt`. Install with `python3 -m pip install -r requirements.txt`.
- **Tests**: Run from repo root with the source on `PYTHONPATH`: `PYTHONPATH=src python3 -m pytest`. Agents should run pytest after every code change.
- **Kalshi API reference**: Treat `reference/kalshi_docs` as the source of truth for API endpoints, request/response shapes, and URL formats; consult it before adding or calling Kalshi APIs.
- **Key files**: `src/kalshi/shared.py` (core helpers), strategy scripts in `src/kalshi/*.py`, TSA prediction helpers in `src/kalshi/create_next_week_prediction.py`.
- **Type hints/docstrings**: Recent changes added type hints and function-level docstrings; keep new code consistent.
- **Secrets**: `.env` and AWS credentials are sensitive; do not log or commit them.

## TSA model system notes (high importance)

- **Strict model mode**: In `prob_source="model"` mode, the code must fail if model inference fails. Do not add silent fallback to heuristics in live or backtest model mode.
  - Enforced in:
    - `src/kalshi/backtest_tsa.py`
    - `src/kalshi/get_current_tsa_market_prices.py`
- **Heuristic mode is explicit**: Heuristic likelihoods should run only when `prob_source="heuristic"`.
- **Production default feature set**: Training defaults to lean core features:
  - `strike_distance_pct`
  - `abs_strike_distance_pct`
  - `day_7_trend`
  - Implemented in `src/kalshi/train_tsa_probability_model.py` (`DEFAULT_LEAN_CORE_FEATURES`).
- **Current production model artifacts**:
  - `src/data/models/tsa_yes_probability_model.joblib`
  - `src/data/models/tsa_yes_probability_model.schema.json`
  - `src/data/models/tsa_yes_probability_model.metadata.json`
- **Backtest audit fields**: Backtest outputs include `prob_source_used`; summaries include `prob_source_model` and `prob_source_heuristic`. Check these when validating runs.

## Useful commands

- Retrain production model (lean-core defaults):
  - `PYTHONPATH=src python3 -m kalshi.train_tsa_probability_model --dataset-csv src/data/datasets/tsa_contract_dataset.csv --target-col y_yes_win --run-date-col run_date --train-weeks 12 --val-weeks 4 --step-weeks 2 --out-model src/data/models/tsa_yes_probability_model.joblib`
- Heuristic backtest:
  - `PYTHONPATH=src python3 -m kalshi.backtest_tsa --start 2024-10-27 --end 2026-02-01 --interval 1440 --cache src/data/tsa_market_history --report-dir src/reports/experiments/tsa_model_compare/heuristic --prob-source heuristic`
- Strict model backtest:
  - `PYTHONPATH=src python3 -m kalshi.backtest_tsa --start 2024-10-27 --end 2026-02-01 --interval 1440 --cache src/data/tsa_market_history --report-dir src/reports/experiments/tsa_model_compare/model --prob-source model --model-bundle src/data/models/tsa_yes_probability_model.joblib`
- Compare two runs:
  - `PYTHONPATH=src python3 -m kalshi.compare_backtests --baseline <baseline_csv> --candidate <candidate_csv> --out <comparison_md>`
- Feature ablation runner:
  - `PYTHONPATH=src python3 -m kalshi.run_tsa_feature_ablation --start 2024-10-27 --end 2026-02-01 --report-dir src/reports/experiments/tsa_feature_ablation --model-dir src/data/models/ablation --cache src/data/tsa_market_history`
- Repo organization/transparency audit:
  - `PYTHONPATH=src python3 -m kalshi.repo_audit`

## Documentation expectations

- Keep `README.md` as the primary operator-facing documentation.
- Keep `ROADMAP.md` aligned with the latest completed milestones and the next concrete tasks.
