import datetime
import json

import pandas as pd

from src.kalshi import build_tsa_contract_dataset
from src.kalshi.clients import HttpError


def test_build_contract_dataset_point_in_time_and_label(monkeypatch):
    event_ticker = "KXTSAW-25DEC07"
    run_date = datetime.date(2025, 11, 30)
    event_date = datetime.date(2025, 12, 7)
    idx = pd.to_datetime([run_date, event_date, datetime.date(2025, 12, 10)])
    passengers = pd.DataFrame(
        {
            "passengers_7_day_moving_average": [2_300_000, 2_500_000, 9_999_999],
        },
        index=idx,
    )

    monkeypatch.setattr(build_tsa_contract_dataset, "build_tsa_events", lambda *_args, **_kwargs: [event_ticker])
    monkeypatch.setattr(build_tsa_contract_dataset.tsa_model, "lag_passengers", lambda: passengers)

    seen_feature_max_date = []

    def fake_get_recent_trend(df, use_weighting=True):
        seen_feature_max_date.append(df.index.max())
        return df

    monkeypatch.setattr(build_tsa_contract_dataset.tsa_model, "get_recent_trend", fake_get_recent_trend)
    monkeypatch.setattr(
        build_tsa_contract_dataset.tsa_model,
        "get_prediction",
        lambda _df, run_date=None: {
            run_date.strftime("%Y-%m-%d"): {
                "prediction": 2_600_000,
                "last_year_passengers": 2_450_000,
                "yoy_adjustment": 1.02,
                "day_1_trend": 1.01,
                "day_7_trend": 1.03,
                "days_until_sunday": 6,
                "most_recent_date": run_date.strftime("%Y-%m-%d"),
            }
        },
    )

    class FakeClient:
        def get_event(self, ticker):
            assert ticker == event_ticker
            return {
                "markets": [
                    {"ticker": f"{event_ticker}-A2.45", "floor_strike": 2_450_000},
                    {"ticker": f"{event_ticker}-BIGNORE", "floor_strike": None},
                ]
            }

    monkeypatch.setattr(build_tsa_contract_dataset.shared, "login", lambda: FakeClient())

    dataset = build_tsa_contract_dataset.build_contract_dataset(
        start_date=datetime.date(2025, 12, 1),
        end_date=datetime.date(2025, 12, 7),
    )

    assert len(dataset) == 1
    assert seen_feature_max_date[0] <= pd.Timestamp(run_date)
    row = dataset.iloc[0]
    assert row["event_ticker"] == event_ticker
    assert row["run_date"] == run_date.isoformat()
    assert row["feature_max_source_date"] == run_date.isoformat()
    assert row["actual_passengers"] == 2_500_000
    assert row["y_yes_win"] == 1
    assert row["floor_strike_millions"] == 2.45


def test_build_contract_dataset_skips_404_events(monkeypatch):
    event_ticker = "KXTSAW-25DEC07"
    run_date = datetime.date(2025, 11, 30)
    event_date = datetime.date(2025, 12, 7)
    idx = pd.to_datetime([run_date, event_date])
    passengers = pd.DataFrame(
        {
            "passengers_7_day_moving_average": [2_300_000, 2_500_000],
        },
        index=idx,
    )

    monkeypatch.setattr(build_tsa_contract_dataset, "build_tsa_events", lambda *_args, **_kwargs: [event_ticker])
    monkeypatch.setattr(build_tsa_contract_dataset.tsa_model, "lag_passengers", lambda: passengers)
    monkeypatch.setattr(build_tsa_contract_dataset.tsa_model, "get_recent_trend", lambda df, use_weighting=True: df)
    monkeypatch.setattr(
        build_tsa_contract_dataset.tsa_model,
        "get_prediction",
        lambda _df, run_date=None: {
            run_date.strftime("%Y-%m-%d"): {
                "prediction": 2_600_000,
                "last_year_passengers": 2_450_000,
                "yoy_adjustment": 1.02,
                "day_1_trend": 1.01,
                "day_7_trend": 1.03,
            }
        },
    )

    class FakeClient:
        def get_event(self, _ticker):
            raise HttpError("Not Found", 404)

    monkeypatch.setattr(build_tsa_contract_dataset.shared, "login", lambda: FakeClient())

    dataset = build_tsa_contract_dataset.build_contract_dataset(
        start_date=datetime.date(2025, 12, 1),
        end_date=datetime.date(2025, 12, 7),
    )
    assert dataset.empty


def test_write_dataset_and_metadata_includes_checksums(monkeypatch, tmp_path):
    dataset = pd.DataFrame([{"event_ticker": "KXTSAW-25DEC07", "y_yes_win": 1}])
    out_csv = tmp_path / "contract_dataset.csv"
    metadata_path = tmp_path / "contract_dataset_meta.json"
    monkeypatch.setattr(
        build_tsa_contract_dataset,
        "_source_file_checksums",
        lambda: {"tsa_data.csv": "abc", "lagged_tsa_data.csv": "def"},
    )

    written = build_tsa_contract_dataset.write_dataset_and_metadata(
        dataset=dataset,
        out_csv=out_csv,
        metadata_json=metadata_path,
        start_date=datetime.date(2025, 12, 1),
        end_date=datetime.date(2025, 12, 7),
    )

    assert written == metadata_path
    meta = json.loads(metadata_path.read_text())
    assert meta["rows"] == 1
    assert meta["dataset_sha256"] == build_tsa_contract_dataset._sha256(out_csv)
    assert meta["source_file_checksums"]["tsa_data.csv"] == "abc"
