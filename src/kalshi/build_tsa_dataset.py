"""Build point-in-time-safe TSA datasets for model training and analysis."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from . import create_next_week_prediction as tsa_model
from .fetch_tsa_history import build_tsa_events


DEFAULT_DATASETS = Path(__file__).resolve().parents[1] / "data" / "datasets"


def _sha256(path: Path) -> str:
    """Return SHA-256 hex digest for the given file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_file_checksums() -> Dict[str, Optional[str]]:
    """Return checksums for core source data files used in dataset generation."""
    data_dir = Path(__file__).resolve().parents[1] / "data"
    checksums: Dict[str, Optional[str]] = {}
    for name in ("tsa_data.csv", "lagged_tsa_data.csv"):
        file_path = data_dir / name
        checksums[name] = _sha256(file_path) if file_path.exists() else None
    return checksums


def build_point_in_time_dataset(
    start_date: datetime.date,
    end_date: datetime.date,
) -> pd.DataFrame:
    """Build one row per weekly TSA event using data available as of each run_date."""
    rows: List[Dict[str, object]] = []
    events = build_tsa_events(start_date, end_date)
    passenger_data = tsa_model.lag_passengers()

    for event_ticker in events:
        date_str = event_ticker.split("-")[-1]
        event_date = datetime.datetime.strptime(date_str, "%y%b%d").date()
        run_date = event_date - datetime.timedelta(days=7)
        run_ts = pd.Timestamp(run_date)

        filtered = passenger_data[passenger_data.index <= run_ts]
        if filtered.empty:
            continue

        filtered = tsa_model.get_recent_trend(filtered, True)
        try:
            prediction = tsa_model.get_prediction(filtered, run_date)
        except (KeyError, ValueError):
            # Skip rows that do not have enough prior-year reference history.
            continue
        pred_key = next(iter(prediction))
        pred = prediction[pred_key]
        pred_passengers = float(pred["prediction"])

        actual_ts = pd.Timestamp(event_date)
        actual = None
        target_percent_error = None
        if actual_ts in passenger_data.index:
            actual_val = float(passenger_data.loc[actual_ts]["passengers_7_day_moving_average"])
            if not pd.isna(actual_val):
                actual = actual_val
                if pred_passengers != 0:
                    target_percent_error = (actual_val / pred_passengers) - 1

        feature_max_source_date = filtered.index.max()
        rows.append(
            {
                "event_ticker": event_ticker,
                "event_date": event_date.isoformat(),
                "run_date": run_date.isoformat(),
                "as_of_date": run_date.isoformat(),
                "feature_max_source_date": feature_max_source_date.date().isoformat(),
                "prediction_passengers": pred_passengers,
                "last_year_passengers": float(pred["last_year_passengers"]),
                "yoy_adjustment": float(pred["yoy_adjustment"]),
                "day_1_trend": float(pred["day_1_trend"]),
                "day_7_trend": float(pred["day_7_trend"]),
                "days_until_sunday": int(pred["days_until_sunday"]),
                "most_recent_tsa_date": str(pred["most_recent_date"]),
                "actual_passengers": actual,
                "target_percent_error": target_percent_error,
            }
        )

    return pd.DataFrame(rows)


def write_dataset_and_metadata(
    dataset: pd.DataFrame,
    out_csv: Path,
    metadata_json: Optional[Path] = None,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
) -> Path:
    """Write dataset CSV and metadata JSON with reproducibility checksums."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(out_csv, index=False)
    dataset_sha256 = _sha256(out_csv)
    metadata_path = metadata_json or out_csv.with_suffix(".json")
    metadata = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "dataset_csv": str(out_csv.resolve()),
        "dataset_sha256": dataset_sha256,
        "rows": int(len(dataset)),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "source_file_checksums": _source_file_checksums(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))
    return metadata_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build point-in-time-safe TSA dataset.")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_DATASETS / "tsa_point_in_time_dataset.csv")
    parser.add_argument("--metadata-json", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    dataset = build_point_in_time_dataset(start_date=start_date, end_date=end_date)
    metadata_path = write_dataset_and_metadata(
        dataset=dataset,
        out_csv=args.out_csv,
        metadata_json=args.metadata_json,
        start_date=start_date,
        end_date=end_date,
    )
    print(args.out_csv)
    print(metadata_path)


if __name__ == "__main__":
    main()
