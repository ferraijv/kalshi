import datetime

import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.kalshi import contract_probability_model as cpm


def test_predict_yes_probability_from_bundle(tmp_path):
    bundle_path = tmp_path / "model.joblib"
    features = ["strike_distance_pct", "day_1_trend"]
    train_x = pd.DataFrame(
        {
            "strike_distance_pct": [-0.10, -0.04, 0.02, 0.08],
            "day_1_trend": [0.98, 1.00, 1.02, 1.04],
        }
    )
    train_y = [0, 0, 1, 1]
    model = Pipeline(steps=[("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=1000))])
    model.fit(train_x, train_y)
    cpm.save_sklearn_bundle(model=model, feature_names=features, model_bundle_path=bundle_path)

    prob_yes = cpm.predict_yes_probability(
        prediction_passengers=2_600_000,
        floor_strike=2_500_000,
        run_date=datetime.date(2025, 12, 1),
        prediction_context={
            "day_1_trend": 1.03,
            "day_7_trend": 1.02,
            "yoy_adjustment": 1.04,
            "last_year_passengers": 2_450_000,
        },
        model_bundle_path=bundle_path,
    )

    assert prob_yes is not None
    assert 0.0 < prob_yes < 1.0
    assert prob_yes > 0.5


def test_map_yes_probability_to_side():
    side, side_prob = cpm.map_yes_probability_to_side(0.2)
    assert side == "no"
    assert side_prob == pytest.approx(0.8)

    side2, side_prob2 = cpm.map_yes_probability_to_side(0.8)
    assert side2 == "yes"
    assert side_prob2 == pytest.approx(0.8)


def test_build_contract_feature_row_includes_floor_strike_millions():
    row = cpm.build_contract_feature_row(
        prediction_passengers=2_500_000,
        floor_strike=2_400_000,
        run_date=datetime.date(2025, 12, 1),
        prediction_context={},
    )
    assert row["floor_strike_millions"] == pytest.approx(2.4)
