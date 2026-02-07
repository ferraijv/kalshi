import datetime
from pathlib import Path

import pandas as pd

from src.kalshi import get_recent_tsa_data as tsa_fetch


class _FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return cls(2026, 1, 1)


class _DateModule:
    datetime = _FixedDateTime


def test_fetch_only_missing_years(monkeypatch, tmp_path):
    # Existing data covers 2019-2022; expect fetch for 2023-2026
    existing_dates = pd.date_range("2019-01-01", "2022-12-31", freq="365D")
    existing = pd.DataFrame({"Date": existing_dates.strftime("%m/%d/%Y"), "Numbers": range(len(existing_dates))})
    data_root = tmp_path
    data_root.mkdir(parents=True, exist_ok=True)
    existing.to_csv(data_root / "tsa_data.csv", index=False)

    called_years = []

    def fake_fetch_year(year_to_process, max_attempts=4):
        called_years.append(year_to_process)
        return pd.DataFrame({"Date": [f"01/01/{year_to_process}"], "Numbers": [year_to_process]})

    monkeypatch.setattr(tsa_fetch, "fetch_year_of_tsa_data", fake_fetch_year)
    monkeypatch.setattr(tsa_fetch, "datetime", _DateModule)

    tsa_fetch.fetch_all_tsa_data(data_root=data_root)

    assert set(called_years) == {2023, 2024, 2025, 2026}

    saved = pd.read_csv(data_root / "tsa_data.csv")
    years_in_file = set(pd.to_datetime(saved["Date"]).dt.year)
    # should include all original + newly fetched years
    assert years_in_file.issuperset({2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026})


def test_csv_columns_preserved(monkeypatch, tmp_path):
    data_root = tmp_path
    data_root.mkdir(parents=True, exist_ok=True)

    def fake_fetch_year(year_to_process, max_attempts=4):
        return pd.DataFrame({"Date": ["01/01/2024"], "Numbers": [123], "Extra": [1]})

    monkeypatch.setattr(tsa_fetch, "fetch_year_of_tsa_data", fake_fetch_year)
    monkeypatch.setattr(tsa_fetch, "datetime", _DateModule)

    out_df = tsa_fetch.fetch_all_tsa_data(data_root=data_root)

    expected_cols = {"Date", "Numbers"}
    assert set(out_df.columns) == expected_cols

    disk_df = pd.read_csv(data_root / "tsa_data.csv")
    assert set(disk_df.columns) == expected_cols
