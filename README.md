# Kalshi Trading Framework

This repository is a lightweight framework for building and running multiple Kalshi trading strategies (daily/weekly index markets, plus experimental TSA traffic plays). Scripts included today are examples; the goal is to host many strategies over time on a shared core.

## Repository layout
- `src/kalshi/clients.py` – signed Kalshi API client (RS256 headers) with market/portfolio helpers.
- `src/kalshi/shared.py` – utilities: login via AWS Secrets Manager, SES email, market ID builders, pricing/backtest helpers, and order helpers (cancel, blanket NOs, sell all, etc.). Treat this as the shared core; new strategies should lean on these helpers.
- Cron-style scripts:
  - `morning.py` – cancel existing S&P orders (demo flag optional) and place blanket NO limit orders.
  - `midday.py` – if no fills yet, cancel outstanding orders.
  - `sp_daily_every_10_minutes.py` – frequent S&P loop: on fills, cancel/replace orders and, if negative risk achieved, re-place higher-price NOs.
  - `afternoon.py` – market-sell all positions in the S&P event near close.
  - `nasdaq_daily_every_10_minutes.py` – finds cheap NASDAQ daily contracts near 1% strike window and buys small YES positions.
  - `before_close.py` – after-close weekly NASDAQ scan using historical likelihood comparison; emails log.
  - `main.py` – sample entry that emails cheap S&P contracts under a price threshold.
- TSA experiments (TSA traffic prediction and trading): `src/kalshi/get_recent_tsa_data.py`, `create_next_week_prediction.py`, `get_current_tsa_market_prices.py`, `place_tsa_orders.py`, `tsa_trading_bot.py`; a second copy lives in `src/tsa_trading_bot/` for legacy use.
- `src/analysis/analysis.py` – scratch file; currently just logs in.
- Data sample: `src/data/historical_data.csv`.

## Configuration
- Environment:
  - `KALSHI_KEY_ID` (required)
  - AWS credentials able to read `kalshi_api_key` (RSA private key PEM) from Secrets Manager and use SES (for emails).
  - Optional `.env` file is read by `shared.login()`.
- Secrets: private key must be stored in Secrets Manager as `kalshi_api_key` unless you change the name in `shared.login`.
- Emails: `shared.send_email` currently hardcodes sender/recipient to `ferraioloj@gmail.com`; adjust before use.

## Running scripts
Install dependencies:
```
pip install -r requirements.txt
```
Run any script with the repo root on `PYTHONPATH`:
```
PYTHONPATH=src python src/kalshi/morning.py
PYTHONPATH=src python src/kalshi/sp_daily_every_10_minutes.py
PYTHONPATH=src python src/kalshi/before_close.py
PYTHONPATH=src python src/kalshi/tsa_trading_bot.py
```
Most scripts assume real-money mode by default; some accept `use_demo=True` inside the code (not CLI-exposed).

## Current limitations / notes
- No command-line interface for toggling demo vs live; edit scripts if needed.
- Strategy logic largely lives inline in scripts; a pluggable strategy registry does not exist yet—add new strategies by creating new scripts or extracting shared pieces into `shared.py`.
- Logging is ad-hoc; some files write to `logs_test.log` but paths are inconsistent.
- Tests are minimal (`test/test_main.py` checks date formatting).

## Why open-source?
The bot is experimental and not yet consistently profitable; sharing it is for discussion and iteration. If it becomes sustainably profitable it may be made private.
