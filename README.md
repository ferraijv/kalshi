# Kalshi Trading Framework

This repository is a lightweight framework for building and running multiple Kalshi trading strategies (daily/weekly index markets, plus experimental TSA traffic plays). Scripts included today are examples; the goal is to host many strategies over time on a shared core.

## Repository layout
- `src/kalshi/clients.py` – signed Kalshi API client (RS256 headers) with market/portfolio helpers.
- `src/kalshi/shared.py` – utilities: login via AWS Secrets Manager, SES email, market ID builders, pricing/backtest helpers, and order helpers (cancel, blanket NOs, sell all, etc.). Treat this as the shared core; new strategies should lean on these helpers.
- `src/kalshi/config.py` – centralized env-backed config loader used by shared/auth/email flows.
- Cron-style scripts:
  - `morning.py` – cancel existing S&P orders (demo flag optional) and place blanket NO limit orders.
  - `midday.py` – if no fills yet, cancel outstanding orders.
  - `sp_daily_every_10_minutes.py` – frequent S&P loop: on fills, cancel/replace orders and, if negative risk achieved, re-place higher-price NOs.
  - `afternoon.py` – market-sell all positions in the S&P event near close.
  - `nasdaq_daily_every_10_minutes.py` – finds cheap NASDAQ daily contracts near 1% strike window and buys small YES positions.
  - `before_close.py` – after-close weekly NASDAQ scan using historical likelihood comparison; emails log.
  - `main.py` – sample entry that emails cheap S&P contracts under a price threshold.
- TSA experiments (TSA traffic prediction and trading): `src/kalshi/get_recent_tsa_data.py`, `create_next_week_prediction.py`, `get_current_tsa_market_prices.py`, `place_tsa_orders.py`, `tsa_trading_bot.py`.
- TSA backtest analysis and comparison tools: `src/kalshi/analyze_backtest_sanity.py`, `src/kalshi/compare_backtests.py`.
- `src/analysis/analysis.py` – scratch file; currently just logs in.
- Data sample: `src/data/historical_data.csv`.

## Configuration
- Environment:
  - `KALSHI_KEY_ID` (required)
  - `KALSHI_PRIVATE_KEY_SECRET` (optional, defaults to `kalshi_api_key`)
  - `AWS_REGION` (optional, defaults to `us-east-1`)
  - `EMAIL_SENDER` and `EMAIL_RECIPIENT` (optional; if unset, email sending is skipped)
  - `DEMO_MODE` (optional boolean; defaults to `false`)
  - AWS credentials able to read the configured private key secret and use SES.
  - Optional `.env` file is loaded by `load_config()`.
- Secrets: private key should be stored in Secrets Manager and referenced via `KALSHI_PRIVATE_KEY_SECRET`.

## Running scripts
Install dependencies:
```
python3 -m pip install -r requirements.txt
```
Run any script with the repo root on `PYTHONPATH`:
```
PYTHONPATH=src python3 src/kalshi/morning.py
PYTHONPATH=src python3 src/kalshi/sp_daily_every_10_minutes.py
PYTHONPATH=src python3 src/kalshi/before_close.py
PYTHONPATH=src python3 src/kalshi/tsa_trading_bot.py
```
Most scripts assume real-money mode by default; some accept `use_demo=True` inside the code (not CLI-exposed).

## TSA backtesting and historical prices
- API reference: see `reference/kalshi_docs` for endpoint shapes and URLs.
- Fetch historical TSA market candlesticks (cached):
  ```
  PYTHONPATH=src python3 -m kalshi.fetch_tsa_history --start 2025-12-01 --end 2026-02-01 --interval 1440
  ```
- Run a rule-based TSA backtest with empirical likelihoods:
  ```
  PYTHONPATH=src python3 -m kalshi.backtest_tsa --start 2025-12-01 --end 2026-02-01 --interval 1440
  ```
  Reports are written to `src/reports/` as CSV and Markdown summaries.

## Phase 0 baseline measurement workflow
- Baseline config: `src/kalshi/configs/tsa_backtest_baseline.json`.
- Run sanity analysis on a backtest CSV:
  ```
  PYTHONPATH=src python3 -m kalshi.analyze_backtest_sanity --csv src/reports/tsa_backtest_<timestamp>.csv
  ```
- `analyze_backtest_sanity` writes:
  - Markdown report: `src/reports/tsa_backtest_sanity_<timestamp>.md`
  - Metadata JSON (run reproducibility + KPIs): `src/reports/tsa_backtest_sanity_<timestamp>.json`
  - Optional metadata override: `--metadata-json /path/to/file.json`
- Compare a candidate run to a baseline run:
  ```
  PYTHONPATH=src python3 -m kalshi.compare_backtests \
    --baseline src/reports/baseline.csv \
    --candidate src/reports/candidate.csv \
    --out src/reports/comparison.md
  ```
  The comparison includes canonical KPIs and absolute/percent deltas.

## Testing
- Run all tests from repo root:
  ```
  PYTHONPATH=src python3 -m pytest
  ```
- Tests live under `test/` and cover date utilities, TSA fetching, backtest logic, sanity metrics, and backtest comparison math.

## Current limitations / notes
- No command-line interface for toggling demo vs live; edit scripts if needed.
- Strategy logic largely lives inline in scripts; a pluggable strategy registry does not exist yet—add new strategies by creating new scripts or extracting shared pieces into `shared.py`.
- Logging is still strategy-specific and not yet standardized across all scripts.

## Why open-source?
The bot is experimental and not yet consistently profitable; sharing it is for discussion and iteration. If it becomes sustainably profitable it may be made private.
