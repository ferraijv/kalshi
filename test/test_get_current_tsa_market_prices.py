import datetime

import pandas as pd
import pytest

from src.kalshi import get_current_tsa_market_prices as prices


def test_get_likelihoods_of_each_contract_uses_model_when_selected(monkeypatch):
    run_date = datetime.date(2025, 12, 1)
    prediction = {
        "2025-12-07": {
            "prediction": 2_550_000,
            "day_1_trend": 1.01,
            "day_7_trend": 1.03,
            "yoy_adjustment": 1.02,
            "last_year_passengers": 2_400_000,
        }
    }

    monkeypatch.setattr(
        prices,
        "get_current_market_prices",
        lambda _run_date: pd.DataFrame(
            [{"ticker": "KXTSAW-25DEC07-A2.45", "floor_strike": 2_450_000, "yes_ask": 55, "no_ask": 45}]
        ),
    )
    monkeypatch.setattr(prices.contract_probability_model, "predict_yes_probability", lambda **_kwargs: 0.81)
    monkeypatch.setattr(prices, "get_likelihood_of_yes", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("heuristic should not run")))
    monkeypatch.setattr(prices, "get_likelihood_of_no", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("heuristic should not run")))

    out = prices.get_likelihoods_of_each_contract(prediction=prediction, run_date=run_date, prob_source="model")
    row = out["KXTSAW-25DEC07-A2.45"]
    assert row["side"] == "yes"
    assert row["true_value"] == 0.81
    assert row["prob_yes"] == 0.81


def test_get_likelihoods_of_each_contract_model_mode_fails_when_model_unavailable(monkeypatch):
    run_date = datetime.date(2025, 12, 1)
    prediction = {
        "2025-12-07": {
            "prediction": 2_350_000,
            "day_1_trend": 0.99,
            "day_7_trend": 0.98,
            "yoy_adjustment": 0.97,
            "last_year_passengers": 2_400_000,
        }
    }

    monkeypatch.setattr(
        prices,
        "get_current_market_prices",
        lambda _run_date: pd.DataFrame(
            [{"ticker": "KXTSAW-25DEC07-A2.45", "floor_strike": 2_450_000, "yes_ask": 55, "no_ask": 45}]
        ),
    )
    monkeypatch.setattr(prices.contract_probability_model, "predict_yes_probability", lambda **_kwargs: None)
    with pytest.raises(RuntimeError, match="refusing heuristic fallback in model mode"):
        prices.get_likelihoods_of_each_contract(prediction=prediction, run_date=run_date, prob_source="model")


def test_get_likelihoods_of_each_contract_uses_heuristic_by_default(monkeypatch):
    run_date = datetime.date(2025, 12, 1)
    prediction = {
        "2025-12-07": {
            "prediction": 2_350_000,
            "day_1_trend": 0.99,
            "day_7_trend": 0.98,
            "yoy_adjustment": 0.97,
            "last_year_passengers": 2_400_000,
        }
    }

    monkeypatch.setattr(
        prices,
        "get_current_market_prices",
        lambda _run_date: pd.DataFrame(
            [{"ticker": "KXTSAW-25DEC07-A2.45", "floor_strike": 2_450_000, "yes_ask": 55, "no_ask": 45}]
        ),
    )
    monkeypatch.setattr(prices.contract_probability_model, "predict_yes_probability", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("model should not run in heuristic mode")))
    monkeypatch.setattr(prices, "_load_historical_likelihood_data", lambda: pd.DataFrame({"percent_error": [0.0]}))
    monkeypatch.setattr(prices, "get_likelihood_of_no", lambda *_args, **_kwargs: 0.7)

    out = prices.get_likelihoods_of_each_contract(prediction=prediction, run_date=run_date)
    row = out["KXTSAW-25DEC07-A2.45"]
    assert row["side"] == "no"
    assert row["prob_yes"] == pytest.approx(0.3)
    assert row["true_value"] == pytest.approx(0.7)
