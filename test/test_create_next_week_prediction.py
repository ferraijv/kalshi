import datetime

import numpy as np
import pandas as pd
import pytest

from src.kalshi import create_next_week_prediction as cnp


def test_get_prediction_raises_when_last_year_reference_is_nan(monkeypatch):
    monkeypatch.setattr(cnp.shared, "get_next_sunday", lambda reference_date=None: "23JAN01")
    monkeypatch.setattr(
        cnp,
        "get_same_date_last_year_day_of_week_adjusted",
        lambda current_year_date: datetime.datetime(2022, 1, 2),
    )
    monkeypatch.setattr(cnp, "get_max_date", lambda tsa_data: pd.Timestamp("2022-12-25"))

    tsa_data = pd.DataFrame(
        {
            "passengers_7_day_moving_average": [np.nan, 100.0],
            "current_trend": [1.0, 1.0],
            "current_trend_1_day": [1.0, 1.0],
        },
        index=pd.to_datetime(["2022-01-02", "2022-12-25"]),
    )

    with pytest.raises(ValueError, match="prior-year reference .* has NaN"):
        cnp.get_prediction(tsa_data, run_date=datetime.date(2022, 12, 26))
