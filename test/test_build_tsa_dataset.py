import datetime
import json

import pandas as pd

from src.kalshi import build_tsa_dataset


def test_build_point_in_time_dataset_uses_only_as_of_history(monkeypatch):
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

    monkeypatch.setattr(build_tsa_dataset, "build_tsa_events", lambda *_args, **_kwargs: [event_ticker])
    monkeypatch.setattr(build_tsa_dataset.tsa_model, "lag_passengers", lambda: passengers)
    monkeypatch.setattr(build_tsa_dataset.tsa_model, "get_recent_trend", lambda df, use_weighting=True: df)

    seen_max_input_date = []

    def fake_get_prediction(df, run_date=None):
        seen_max_input_date.append(df.index.max())
        return {
            run_date.strftime("%Y-%m-%d"): {
                "prediction": 2_400_000,
                "last_year_passengers": 2_300_000,
                "yoy_adjustment": 1.01,
                "day_1_trend": 1.02,
                "day_7_trend": 1.00,
                "days_until_sunday": 6,
                "most_recent_date": run_date.strftime("%Y-%m-%d"),
            }
        }

    monkeypatch.setattr(build_tsa_dataset.tsa_model, "get_prediction", fake_get_prediction)

    dataset = build_tsa_dataset.build_point_in_time_dataset(
        start_date=datetime.date(2025, 12, 1),
        end_date=datetime.date(2025, 12, 7),
    )

    assert len(dataset) == 1
    assert seen_max_input_date[0] <= pd.Timestamp(run_date)
    assert dataset.iloc[0]["feature_max_source_date"] == run_date.isoformat()
    assert dataset.iloc[0]["actual_passengers"] == 2_500_000


def test_write_dataset_and_metadata_includes_checksums(monkeypatch, tmp_path):
    dataset = pd.DataFrame([{"event_ticker": "KXTSAW-25DEC07", "prediction_passengers": 2_400_000}])
    out_csv = tmp_path / "dataset.csv"
    metadata_path = tmp_path / "dataset_meta.json"
    monkeypatch.setattr(
        build_tsa_dataset,
        "_source_file_checksums",
        lambda: {"tsa_data.csv": "abc", "lagged_tsa_data.csv": "def"},
    )

    written_meta = build_tsa_dataset.write_dataset_and_metadata(
        dataset=dataset,
        out_csv=out_csv,
        metadata_json=metadata_path,
        start_date=datetime.date(2025, 12, 1),
        end_date=datetime.date(2025, 12, 7),
    )

    assert written_meta == metadata_path
    meta = json.loads(metadata_path.read_text())
    assert meta["rows"] == 1
    assert meta["dataset_sha256"] == build_tsa_dataset._sha256(out_csv)
    assert meta["source_file_checksums"]["tsa_data.csv"] == "abc"
