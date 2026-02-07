import datetime
import pandas as pd
import pytest

from src.kalshi import backtest_tsa


def test_calc_fill_price_prefers_bid_ask():
    df = pd.DataFrame({"yes_bid.close": [30], "yes_ask.close": [50]})
    assert backtest_tsa._calc_fill_price(df) == 0.4  # (30+50)/2 / 100

    df2 = pd.DataFrame({"price.close": [60]})
    assert backtest_tsa._calc_fill_price(df2) == 0.6

    df3 = pd.DataFrame({"high": [80], "low": [20]})
    assert backtest_tsa._calc_fill_price(df3) == 0.5


def test_backtest_range_happy_path(monkeypatch, tmp_path):
    # Fake passenger data
    run_date = datetime.date(2025, 11, 30)
    event_date = datetime.date(2025, 12, 7)
    idx = pd.to_datetime([run_date, event_date])
    passengers = pd.DataFrame(
        {
            "passengers": [2_500_000, 2_500_000],
            "previous_year": [2_400_000, 2_400_000],
            "passengers_7_day_moving_average": [2_500_000, 2_500_000],
            "passengers_7_day_moving_average_previous_year": [2_400_000, 2_400_000],
        },
        index=idx,
    )

    monkeypatch.setattr(backtest_tsa.tsa_model, "lag_passengers", lambda: passengers)
    monkeypatch.setattr(backtest_tsa.tsa_model, "get_recent_trend", lambda df, use_weighting=True: df)

    def fake_get_prediction(df, run_date=None):
        return {run_date.strftime("%Y-%m-%d"): {"prediction": 2_600_000}}

    monkeypatch.setattr(backtest_tsa.tsa_model, "get_prediction", fake_get_prediction)

    class FakeClient:
        def get_event(self, event_ticker):
            return {
                "markets": [
                    {"ticker": f"{event_ticker}-A2.05", "floor_strike": 2_450_000},
                    {"ticker": f"{event_ticker}-BIGNORE", "floor_strike": None},
                ]
            }

    monkeypatch.setattr(backtest_tsa.shared, "login", lambda: FakeClient())

    def fake_fetch_market_candles(ticker, start_ts, end_ts, interval_minutes, cache_dir, client, include_latest_before_start=False):
        # simple tight market mid = 0.6
        return pd.DataFrame({"yes_bid.close": [55], "yes_ask.close": [65]})

    monkeypatch.setattr(backtest_tsa, "fetch_market_candles", fake_fetch_market_candles)

    df = backtest_tsa.backtest_range(
        start_date=datetime.date(2025, 11, 1),
        end_date=datetime.date(2025, 12, 7),
        interval_minutes=1440,
        cache_dir=tmp_path,
        include_latest_before_start=False,
    )

    assert len(df) == 1  # second market missing floor_strike skipped
    row = df.iloc[0]
    assert row["market"].endswith("A2.05")
    assert 0.5 <= row["prob"] <= 0.999
    assert row["fill_price"] == 0.6


def test_backtest_settles_on_event_date_not_run_date(monkeypatch, tmp_path):
    event_ticker = "KXTSAW-25DEC07"
    run_date = datetime.date(2025, 11, 30)
    event_date = datetime.date(2025, 12, 7)
    idx = pd.to_datetime([run_date, event_date])
    passengers = pd.DataFrame(
        {
            "passengers": [2_300_000, 2_500_000],
            "previous_year": [2_200_000, 2_400_000],
            "passengers_7_day_moving_average": [2_300_000, 2_500_000],
            "passengers_7_day_moving_average_previous_year": [2_200_000, 2_400_000],
        },
        index=idx,
    )
    hist = pd.DataFrame(
        {
            "passengers_7_day_moving_average": [100.0, 101.0],
            "prediction": [100.0, 100.0],
            "day_of_week": ["Sunday", "Sunday"],
        }
    )

    monkeypatch.setattr(backtest_tsa, "build_tsa_events", lambda start, end: [event_ticker])
    monkeypatch.setattr(backtest_tsa.tsa_model, "lag_passengers", lambda: passengers)
    monkeypatch.setattr(backtest_tsa.tsa_model, "get_recent_trend", lambda df, use_weighting=True: df)
    monkeypatch.setattr(
        backtest_tsa.tsa_model,
        "get_prediction",
        lambda df, run_date=None: {run_date.strftime("%Y-%m-%d"): {"prediction": 2_600_000}},
    )
    monkeypatch.setattr(backtest_tsa.pd, "read_csv", lambda *_args, **_kwargs: hist)
    monkeypatch.setattr(backtest_tsa, "get_likelihood_of_yes", lambda *_args, **_kwargs: 0.9)

    class FakeClient:
        def get_event(self, ticker):
            assert ticker == event_ticker
            return {"markets": [{"ticker": f"{event_ticker}-A2.45", "floor_strike": 2_450_000}]}

    monkeypatch.setattr(backtest_tsa.shared, "login", lambda: FakeClient())
    monkeypatch.setattr(
        backtest_tsa,
        "fetch_market_candles",
        lambda *_args, **_kwargs: pd.DataFrame({"yes_bid.close": [55], "yes_ask.close": [65]}),
    )

    df = backtest_tsa.backtest_range(
        start_date=datetime.date(2025, 12, 1),
        end_date=datetime.date(2025, 12, 7),
        interval_minutes=1440,
        cache_dir=tmp_path,
    )

    assert len(df) == 1
    row = df.iloc[0]
    assert row["outcome"] == 1
    assert row["pnl"] == 0.4


def test_backtest_no_side_and_pnl_uses_no_contract_pricing(monkeypatch, tmp_path):
    event_ticker = "KXTSAW-25DEC07"
    run_date = datetime.date(2025, 11, 30)
    event_date = datetime.date(2025, 12, 7)
    idx = pd.to_datetime([run_date, event_date])
    passengers = pd.DataFrame(
        {
            "passengers": [2_350_000, 2_350_000],
            "previous_year": [2_200_000, 2_200_000],
            "passengers_7_day_moving_average": [2_350_000, 2_350_000],
            "passengers_7_day_moving_average_previous_year": [2_200_000, 2_200_000],
        },
        index=idx,
    )
    hist = pd.DataFrame(
        {
            "passengers_7_day_moving_average": [100.0, 101.0],
            "prediction": [100.0, 100.0],
            "day_of_week": ["Sunday", "Sunday"],
        }
    )

    monkeypatch.setattr(backtest_tsa, "build_tsa_events", lambda start, end: [event_ticker])
    monkeypatch.setattr(backtest_tsa.tsa_model, "lag_passengers", lambda: passengers)
    monkeypatch.setattr(backtest_tsa.tsa_model, "get_recent_trend", lambda df, use_weighting=True: df)
    monkeypatch.setattr(
        backtest_tsa.tsa_model,
        "get_prediction",
        lambda df, run_date=None: {run_date.strftime("%Y-%m-%d"): {"prediction": 2_300_000}},
    )
    monkeypatch.setattr(backtest_tsa.pd, "read_csv", lambda *_args, **_kwargs: hist)
    monkeypatch.setattr(backtest_tsa, "get_likelihood_of_no", lambda *_args, **_kwargs: 0.7)

    class FakeClient:
        def get_event(self, ticker):
            assert ticker == event_ticker
            return {"markets": [{"ticker": f"{event_ticker}-A2.45", "floor_strike": 2_450_000}]}

    monkeypatch.setattr(backtest_tsa.shared, "login", lambda: FakeClient())
    monkeypatch.setattr(
        backtest_tsa,
        "fetch_market_candles",
        lambda *_args, **_kwargs: pd.DataFrame({"yes_bid.close": [15], "yes_ask.close": [25]}),
    )

    df = backtest_tsa.backtest_range(
        start_date=datetime.date(2025, 12, 1),
        end_date=datetime.date(2025, 12, 7),
        interval_minutes=1440,
        cache_dir=tmp_path,
    )

    assert len(df) == 1
    row = df.iloc[0]
    assert row["outcome"] == 1
    assert row["pnl"] == pytest.approx(0.2)
