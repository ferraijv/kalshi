"""Rolling backtest for TSA rule-based model using historical Kalshi prices."""

from __future__ import annotations

import argparse
import datetime
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from . import shared
from . import create_next_week_prediction as tsa_model
from .fetch_tsa_history import fetch_market_candles, build_tsa_events
from .get_current_tsa_market_prices import (
    get_likelihood_of_yes,
    get_likelihood_of_no,
)


DEFAULT_REPORTS = Path(__file__).resolve().parents[1] / "reports"
DEFAULT_CACHE = Path(__file__).resolve().parents[1] / "data" / "tsa_market_history"


@dataclass
class BacktestResult:
    market: str
    date: datetime.date
    side: str
    prob: float
    fill_price: float
    outcome: int
    pnl: float
    brier: float
    logloss: float
    edge: float


def _calc_fill_price(candles: pd.DataFrame) -> float:
    """Return an implied fill probability from candlestick data (mid of bid/ask if present)."""
    if candles.empty:
        return np.nan
    # Prefer bid/ask closes if present (in cents)
    yes_bid_close = candles.get("yes_bid.close")
    yes_ask_close = candles.get("yes_ask.close")
    if yes_bid_close is not None and yes_ask_close is not None:
        mid_cents = (yes_bid_close.iloc[0] + yes_ask_close.iloc[0]) / 2
    elif "price.close" in candles.columns:
        mid_cents = candles["price.close"].iloc[0]
    elif "high" in candles.columns and "low" in candles.columns:
        mid_cents = (candles["high"].iloc[0] + candles["low"].iloc[0]) / 2
    else:
        return np.nan
    return float(mid_cents / 100)  # convert cents->prob


def _calc_outcome(actual_passengers: float, floor_strike: float, side: str) -> int:
    """Return 1 if the chosen side wins given actual passengers vs strike, else 0."""
    outcome_yes = int(actual_passengers >= floor_strike)
    return outcome_yes if side == "yes" else 1 - outcome_yes


def backtest_range(
    start_date: datetime.date,
    end_date: datetime.date,
    interval_minutes: int = 1440,
    cache_dir: Path = DEFAULT_CACHE,
    include_latest_before_start: bool = False,
) -> pd.DataFrame:
    """Run a rolling TSA backtest over a date range using historical candlesticks and empirical likelihoods."""
    results: List[BacktestResult] = []

    events = build_tsa_events(start_date, end_date)
    passenger_data = tsa_model.lag_passengers()
    client = shared.login()
    # historical error data for calibration (mirrors live likelihood calc)
    data_path = Path(__file__).resolve().parents[1] / "data" / "lagged_tsa_data.csv"
    hist = pd.read_csv(data_path)
    hist = hist[["passengers_7_day_moving_average", "prediction", "day_of_week"]]
    hist = hist[~hist["prediction"].isna()]
    hist["percent_error"] = hist["passengers_7_day_moving_average"] / hist["prediction"] - 1

    for event_ticker in events:
        date_str = event_ticker.split("-")[-1]
        event_date = datetime.datetime.strptime(date_str, "%y%b%d").date()
        run_date = event_date - datetime.timedelta(days=7)

        # prediction using data available up to run_date
        filtered = passenger_data[passenger_data.index <= pd.Timestamp(run_date)]
        if filtered.empty:
            continue
        filtered = tsa_model.get_recent_trend(filtered, True)
        prediction = tsa_model.get_prediction(filtered, run_date)
        pred_key = next(iter(prediction))
        pred_passengers = float(prediction[pred_key]["prediction"])

        event = client.get_event(event_ticker)
        for market in event.get("markets", []):
            market_ticker = market["ticker"]

            floor_strike = market.get("floor_strike")
            if floor_strike is None:
                continue

            start_ts = int(datetime.datetime.combine(run_date, datetime.time()).timestamp())
            end_ts = int(datetime.datetime.combine(event_date, datetime.time()).timestamp())
            candles = fetch_market_candles(
                market_ticker,
                start_ts,
                end_ts,
                interval_minutes,
                cache_dir=cache_dir,
                client=client,
                include_latest_before_start=include_latest_before_start,
            )
            fill_price = _calc_fill_price(candles)
            if np.isnan(fill_price):
                continue

            actual_ts = pd.Timestamp(event_date)
            if actual_ts not in passenger_data.index:
                continue
            actual = float(passenger_data.loc[actual_ts]["passengers_7_day_moving_average"])
            if np.isnan(actual):
                continue

            if pred_passengers > floor_strike:
                side = "yes"
                prob = get_likelihood_of_yes(pred_passengers, floor_strike, hist)
            elif pred_passengers < floor_strike:
                side = "no"
                prob = get_likelihood_of_no(pred_passengers, floor_strike, hist)
            else:
                # No directional edge when prediction equals strike.
                continue

            outcome = _calc_outcome(actual, floor_strike, side)

            contract_price = fill_price if side == "yes" else 1 - fill_price
            edge = prob - contract_price
            pnl = (1 - contract_price) if outcome == 1 else (-contract_price)
            brier = (prob - outcome) ** 2
            prob_clipped = float(np.clip(prob, 1e-9, 1 - 1e-9))
            logloss = -(outcome * np.log(prob_clipped) + (1 - outcome) * np.log(1 - prob_clipped))

            results.append(
                BacktestResult(
                    market=market_ticker,
                    date=event_date,
                    side=side,
                    prob=prob,
                    fill_price=fill_price,
                    outcome=outcome,
                    pnl=pnl,
                    brier=brier,
                    logloss=logloss,
                    edge=edge,
                )
            )

    return pd.DataFrame([r.__dict__ for r in results])


def summarize(df: pd.DataFrame) -> Dict[str, float]:
    """Return aggregate metrics from a backtest results DataFrame."""
    if df.empty:
        return {}
    return {
        "trades": len(df),
        "pnl_total": df.pnl.sum(),
        "pnl_avg": df.pnl.mean(),
        "brier": df.brier.mean(),
        "logloss": df.logloss.mean(),
        "edge_avg": df.edge.mean(),
    }


def save_report(df: pd.DataFrame, out_dir: Path) -> None:
    """Persist detailed CSV and a short Markdown summary for a backtest run."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(out_dir / f"tsa_backtest_{ts}.csv", index=False)
    summary = summarize(df)
    with open(out_dir / f"tsa_backtest_{ts}.md", "w") as f:
        f.write("# TSA Backtest\n\n")
        for k, v in summary.items():
            f.write(f"- {k}: {v}\n")


def main():
    """CLI entrypoint to run the TSA backtest and emit reports."""
    parser = argparse.ArgumentParser(description="Run TSA backtest with historical Kalshi prices")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--interval", type=int, default=1440, help="Candlestick interval in minutes")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="Cache directory")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORTS, help="Output reports dir")
    parser.add_argument("--include-latest-before-start", action="store_true", help="Include synthetic candle before start_ts")
    args = parser.parse_args()

    df = backtest_range(
        start_date=datetime.date.fromisoformat(args.start),
        end_date=datetime.date.fromisoformat(args.end),
        interval_minutes=args.interval,
        cache_dir=args.cache,
        include_latest_before_start=args.include_latest_before_start,
    )
    save_report(df, args.report_dir)
    print(summarize(df))


if __name__ == "__main__":
    main()
