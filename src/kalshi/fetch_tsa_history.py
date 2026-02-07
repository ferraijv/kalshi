"""Utilities to pull and cache TSA market history from Kalshi."""

from __future__ import annotations

import argparse
import datetime
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from . import shared


def _split_series_market(ticker: str) -> tuple[str, str]:
    """Split a market ticker into (series_ticker, full_market_ticker)."""
    if "-" not in ticker:
        raise ValueError(f"Unexpected ticker format: {ticker}")
    series, rest = ticker.split("-", 1)
    return series, ticker  # series_ticker, full market ticker


DEFAULT_CACHE = Path(__file__).resolve().parents[1] / "data" / "tsa_market_history"


def _login(client=None):
    """Return provided client or log in via shared.login()."""
    return client or shared.login()


def fetch_market_candles(
    market_ticker: str,
    start_ts: int,
    end_ts: int,
    interval_minutes: int = 1440,
    cache_dir: Path = DEFAULT_CACHE,
    client=None,
    include_latest_before_start: bool = False,
) -> pd.DataFrame:
    """Fetch candlesticks for a market, cached by ticker+interval."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{market_ticker}_{interval_minutes}m.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)

    exchange = _login(client)
    if not hasattr(exchange, "get_market_candlesticks"):
        raise NotImplementedError("Exchange client lacks get_market_candlesticks; update client or mock for offline use.")

    series_ticker, market_only = _split_series_market(market_ticker)

    candles = exchange.get_market_candlesticks(
        series_ticker=series_ticker,
        ticker=market_only,
        start_ts=start_ts,
        end_ts=end_ts,
        period_interval=interval_minutes,
        include_latest_before_start=include_latest_before_start,
    )
    rows = candles.get("candlesticks", candles)
    df = pd.json_normalize(rows)
    if not df.empty:
        ts_col = "end_period_ts" if "end_period_ts" in df.columns else "timestamp"
        df["end_ts"] = pd.to_datetime(df[ts_col], unit="s")
        df.to_parquet(cache_path, index=False)
    return df


def build_tsa_events(start_date: datetime.date, end_date: datetime.date) -> list[str]:
    """Return TSA event tickers (one per Sunday) in [start, end]."""
    tickers = []
    day = start_date
    while day <= end_date:
        if day.weekday() == 6:  # Sunday
            ticker = shared.create_tsa_event_id(shared.format_date(day))
            tickers.append(ticker)
        day += datetime.timedelta(days=1)
    return tickers


def main():
    """CLI to pull and cache TSA market candlesticks for a date range."""
    parser = argparse.ArgumentParser(description="Fetch TSA market candlesticks with caching.")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--interval", type=int, default=1440, help="Candlestick interval in minutes")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="Cache directory")
    parser.add_argument("--include-latest-before-start", action="store_true", help="Include latest candle before start_ts")
    args = parser.parse_args()

    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    events = build_tsa_events(start_date, end_date)
    client = _login()

    for event in events:
        # rough bounds: one week around each event
        event_date = datetime.datetime.strptime(event.split("-")[-1], "%y%b%d").date()
        start_ts = int(datetime.datetime.combine(event_date - datetime.timedelta(days=7), datetime.time()).timestamp())
        end_ts = int(datetime.datetime.combine(event_date, datetime.time()).timestamp())
        logging.info(f"Fetching event {event} candlesticks")
        event_obj = client.get_event(event)
        for market in event_obj.get("markets", []):
            fetch_market_candles(
                market["ticker"],
                start_ts,
                end_ts,
                args.interval,
                cache_dir=args.cache,
                client=client,
                include_latest_before_start=args.include_latest_before_start,
            )


if __name__ == "__main__":
    main()
