import pytest

pytest.importorskip("streamlit")

import pandas as pd

from src.kalshi.ui import backtest_range, get_backtest_horizon, MarketRow


def test_backtest_range_counts_samples():
    markets = [
        MarketRow(
            ticker="ABC",
            subtitle="Range",
            yes_bid=10,
            yes_ask=12,
            no_bid=88,
            no_ask=90,
            floor_strike=0.98,
            cap_strike=1.02,
        )
    ]

    history = pd.DataFrame({"Close": [100, 101, 99, 101]})
    results = backtest_range(markets, history, horizon_days=1)

    assert not results.empty
    assert results.iloc[0]["Samples"] == 3


def test_get_backtest_horizon_matches_event_type():
    assert get_backtest_horizon("INXW-TEST") == 5
    assert get_backtest_horizon("NASDAQ100D-TEST") == 1
