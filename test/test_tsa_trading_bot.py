import datetime

from src.kalshi import tsa_trading_bot


def test_compute_likelihoods_for_both_sources_runs_both(monkeypatch):
    prediction = {"2025-12-07": {"prediction": 2_500_000}}

    def fake_get_likelihoods(prediction, run_date=None, prob_source="heuristic"):
        return {f"{prob_source}-ticker": {"side": "yes", "true_value": 0.8, "floor_strike": 2_450_000}}

    monkeypatch.setattr(tsa_trading_bot, "get_likelihoods_of_each_contract", fake_get_likelihoods)

    results, errors = tsa_trading_bot._compute_likelihoods_for_both_sources(
        prediction=prediction,
        run_date=datetime.date(2025, 12, 1),
    )

    assert "heuristic" in results
    assert "model" in results
    assert not errors


def test_compute_likelihoods_for_both_sources_captures_error(monkeypatch):
    prediction = {"2025-12-07": {"prediction": 2_500_000}}

    def fake_get_likelihoods(prediction, run_date=None, prob_source="heuristic"):
        if prob_source == "model":
            raise RuntimeError("model failed")
        return {f"{prob_source}-ticker": {"side": "yes", "true_value": 0.8, "floor_strike": 2_450_000}}

    monkeypatch.setattr(tsa_trading_bot, "get_likelihoods_of_each_contract", fake_get_likelihoods)

    results, errors = tsa_trading_bot._compute_likelihoods_for_both_sources(
        prediction=prediction,
        run_date=datetime.date(2025, 12, 1),
    )

    assert "heuristic" in results
    assert "model" not in results
    assert errors["model"] == "model failed"


def test_format_email_includes_both_sources_and_errors():
    prediction = {
        "2025-12-07": {
            "prediction": 2_550_000,
            "yoy_adjustment": 1.01,
            "day_1_trend": 1.02,
            "day_7_trend": 1.03,
            "last_year_passengers": 2_450_000,
            "days_until_sunday": 6,
            "most_recent_date": "2025-12-01",
        }
    }
    heuristic = {
        "KXTSAW-25DEC07-A2.45": {"floor_strike": 2_450_000, "side": "yes", "true_value": 0.81}
    }
    model = {
        "KXTSAW-25DEC07-A2.50": {"floor_strike": 2_500_000, "side": "no", "true_value": 0.62}
    }
    errors = {"model": "schema mismatch"}

    body = tsa_trading_bot._format_email(
        prediction=prediction,
        heuristic_likelihoods=heuristic,
        model_likelihoods=model,
        errors=errors,
        orders="No orders placed today",
    )

    assert "Trading mode: heuristic" in body
    assert "Heuristic likelihoods" in body
    assert "Model likelihoods" in body
    assert "schema mismatch" in body
    assert "Orders:" in body
