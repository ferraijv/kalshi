"""Streamlit UI for exploring Kalshi markets and helper analytics.

Run with:

```
streamlit run src/kalshi/ui.py
```

Ensure your ``PYTHONPATH`` includes the repository ``src`` directory so the
package imports resolve (for example ``PYTHONPATH=src streamlit run ...``).
"""

from __future__ import annotations

import datetime
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import streamlit as st
import yfinance as yf

# Allow running via ``streamlit run`` without installing as a package.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from kalshi import shared


@dataclass
class MarketRow:
    """Minimal shape for displaying market information in the UI."""

    ticker: str
    subtitle: str
    yes_bid: Optional[float]
    yes_ask: Optional[float]
    no_bid: Optional[float]
    no_ask: Optional[float]
    floor_strike: Optional[float]
    cap_strike: Optional[float]

    @classmethod
    def from_market(cls, market: dict) -> "MarketRow":
        return cls(
            ticker=market.get("ticker", ""),
            subtitle=market.get("subtitle", ""),
            yes_bid=market.get("yes_bid"),
            yes_ask=market.get("yes_ask"),
            no_bid=market.get("no_bid"),
            no_ask=market.get("no_ask"),
            floor_strike=market.get("floor_strike"),
            cap_strike=market.get("cap_strike"),
        )


SAMPLE_EVENT = {
    "ticker": "NASDAQ100D-SAMPLE",
    "title": "Sample Nasdaq Daily",
    "markets": [
        {
            "ticker": "NAS_NO_CHANGE",
            "subtitle": "Close within ±1%",
            "yes_bid": 35,
            "yes_ask": 38,
            "no_bid": 63,
            "no_ask": 66,
            "floor_strike": 0.99,
            "cap_strike": 1.01,
        },
        {
            "ticker": "NAS_UP_BIG",
            "subtitle": "Close 2% or more above",
            "yes_bid": 12,
            "yes_ask": 15,
            "no_bid": 85,
            "no_ask": 88,
            "floor_strike": 1.02,
            "cap_strike": None,
        },
        {
            "ticker": "NAS_DOWN_BIG",
            "subtitle": "Close 2% or more below",
            "yes_bid": 9,
            "yes_ask": 11,
            "no_bid": 89,
            "no_ask": 91,
            "floor_strike": None,
            "cap_strike": 0.98,
        },
    ],
}


def build_market_table(markets: Iterable[MarketRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": market.ticker,
                "Contract": market.subtitle,
                "Yes Bid": market.yes_bid,
                "Yes Ask": market.yes_ask,
                "No Bid": market.no_bid,
                "No Ask": market.no_ask,
                "Floor Strike": market.floor_strike,
                "Cap Strike": market.cap_strike,
            }
            for market in markets
        ]
    )


def get_market_rows(event: dict) -> List[MarketRow]:
    return [MarketRow.from_market(market) for market in event.get("markets", [])]


def filter_by_price_threshold(markets: List[MarketRow], threshold: float) -> List[MarketRow]:
    return [market for market in markets if (market.yes_ask or 0) < threshold or (market.no_ask or 0) < threshold]


def display_range_analysis(markets: List[MarketRow], current_price: float) -> None:
    rows = []
    for market in markets:
        if market.floor_strike or market.cap_strike:
            lower, upper = shared.get_percentage_change_for_market(current_price, market.__dict__)
            rows.append(
                {
                    "Ticker": market.ticker,
                    "Contract": market.subtitle,
                    "Lower %": round((lower - 1) * 100, 2),
                    "Upper %": round((upper - 1) * 100, 2),
                }
            )

    if rows:
        st.subheader("Movement range vs. current price")
        st.dataframe(pd.DataFrame(rows))
    else:
        st.info("No strike information available to calculate movement ranges.")


def load_event_from_api(exchange_client, event_id: str) -> Optional[dict]:
    try:
        event = exchange_client.get_event(event_id)
        return event.get("event") or event
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unable to load event {event_id}: {exc}")
        return None


def show_header():
    st.title("Kalshi Trading Workbench")
    st.caption(
        "Dashboard to browse markets, flag cheap contracts, and sanity-check strike ranges."
    )


def render_sidebar() -> dict:
    st.sidebar.header("Data Source")
    source = st.sidebar.radio("Select where to load markets", ["Demo", "Kalshi API"], index=0)

    default_event = shared.create_nasdaq_event_id(datetime.date.today())
    if datetime.date.today().weekday() == 4:
        default_event = shared.create_weekly_nasdaq_market_id()

    event_id = st.sidebar.text_input("Event ticker", value=default_event)

    current_price = st.sidebar.number_input(
        "Current index level for range math", value=18000.0, step=50.0
    )

    st.sidebar.markdown(
        "Use the API option after setting `KALSHI_KEY_ID` in your environment and"
        " storing your private key PEM in the `kalshi_api_key` secret."
    )

    return {"source": source, "event_id": event_id, "current_price": current_price}


def ensure_client(source: str):
    if source != "Kalshi API":
        return None

    if "exchange_client" in st.session_state:
        return st.session_state["exchange_client"]

    with st.spinner("Connecting to Kalshi..."):
        client = shared.login()
        st.session_state["exchange_client"] = client
        return client


def load_event(source: str, event_id: str, exchange_client) -> Optional[dict]:
    if source == "Demo":
        return SAMPLE_EVENT

    if not exchange_client:
        st.error("Exchange client unavailable; check credentials and try again.")
        return None

    return load_event_from_api(exchange_client, event_id)


def render_market_tables(markets: List[MarketRow]) -> None:
    st.subheader("All contracts")
    st.dataframe(build_market_table(markets), use_container_width=True)

    threshold = st.slider("Highlight contracts with asks below", min_value=1, max_value=80, value=20)
    filtered = filter_by_price_threshold(markets, threshold)
    if filtered:
        st.markdown(f"Contracts with asks below **{threshold}** cents")
        st.dataframe(build_market_table(filtered), use_container_width=True)
    else:
        st.info("No contracts under the selected threshold.")


def get_backtest_horizon(event_id: str) -> int:
    """Infer lookahead days from the event ticker."""

    if "W-" in event_id:
        return 5
    if "D-" in event_id:
        return 1
    return 1


@st.cache_data(show_spinner=False)
def fetch_index_history(symbol: str, lookback_days: int) -> pd.DataFrame:
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=lookback_days)
    history = yf.download(symbol, start=start_date, end=end_date)
    if history.empty:
        raise ValueError(f"No history returned for {symbol} between {start_date} and {end_date}.")
    return history


def backtest_range(markets: List[MarketRow], history: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    closes = history.get("Close")
    if closes is None or closes.empty or len(closes) <= horizon_days:
        return pd.DataFrame()

    results = []
    for market in markets:
        if market.floor_strike is None and market.cap_strike is None:
            continue

        wins = 0
        samples = 0
        for idx in range(len(closes) - horizon_days):
            start_price = closes.iloc[idx]
            end_price = closes.iloc[idx + horizon_days]

            lower_bound = -float("inf") if market.floor_strike is None else market.floor_strike * start_price
            upper_bound = float("inf") if market.cap_strike is None else market.cap_strike * start_price

            samples += 1
            if lower_bound <= end_price <= upper_bound:
                wins += 1

        if samples:
            results.append(
                {
                    "Ticker": market.ticker,
                    "Contract": market.subtitle,
                    "Win Rate": round((wins / samples) * 100, 2),
                    "Samples": samples,
                }
            )

    return pd.DataFrame(results)


def render_backtest_panel(markets: List[MarketRow], event_id: str) -> None:
    st.subheader("Backtest strike ranges against index history")

    symbol = st.selectbox(
        "Index for backtesting",
        options=["^NDX", "^GSPC", "QQQ", "SPY"],
        index=0 if "NASDAQ" in event_id else 1,
        help="Choose the underlying index ETF or cash index matching the event.",
    )
    lookback_days = st.slider("Lookback window (days)", min_value=60, max_value=1095, value=365, step=15)
    horizon_days = get_backtest_horizon(event_id)

    st.caption(
        "Win rate shows how often the closing price after the lookahead window stays within each contract's "
        "floor/cap strike range using historical data."
    )

    if st.button("Run backtest", key="backtest"):
        with st.spinner("Running backtest..."):
            try:
                history = fetch_index_history(symbol, lookback_days)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unable to load history for {symbol}: {exc}")
                return

            results = backtest_range(markets, history, horizon_days)
            if results.empty:
                st.warning("Not enough data to compute backtest results.")
            else:
                st.dataframe(results, use_container_width=True)


def main():
    show_header()
    options = render_sidebar()
    exchange_client = ensure_client(options["source"])

    if st.button("Load markets", type="primary"):
        event = load_event(options["source"], options["event_id"], exchange_client)
        if not event:
            return

        st.success(f"Loaded {event.get('ticker')} – {event.get('title', 'No title')}")
        markets = get_market_rows(event)
        render_market_tables(markets)
        display_range_analysis(markets, options["current_price"])
        render_backtest_panel(markets, event.get("ticker", options["event_id"]))
    else:
        st.info("Set the event ticker and click **Load markets** to begin.")


if __name__ == "__main__":
    main()
