import datetime
import types

import pytest

from src.kalshi import shared
from src.kalshi.create_next_week_prediction import (
    calculate_days_until_sunday,
    get_same_date_last_year_day_of_week_adjusted,
)


def test_format_date():
    dt = datetime.datetime.strptime("20230801", "%Y%m%d")
    assert shared.format_date(dt) == "23AUG01"


def test_create_sp_market_id_daily():
    dt = datetime.datetime.strptime("20230323", "%Y%m%d")
    assert shared.create_sp_market_id(dt) == "INXD-23MAR23"


def test_create_sp_market_id_weekly():
    dt = datetime.datetime.strptime("20230324", "%Y%m%d")  # Friday
    assert shared.create_sp_market_id(dt) == "INXW-23MAR24"


def test_create_nasdaq_event_id_daily():
    dt = datetime.datetime.strptime("20240103", "%Y%m%d")  # Wednesday
    assert shared.create_nasdaq_event_id(dt) == "NASDAQ100D-24JAN03"


def test_create_nasdaq_event_id_weekly():
    dt = datetime.datetime.strptime("20240105", "%Y%m%d")  # Friday
    assert shared.create_nasdaq_event_id(dt) == "NASDAQ100W-24JAN05"


def _patch_today(monkeypatch, module, target_date: datetime.date):
    """Monkeypatch module.datetime.date.today to return target_date."""

    class PatchedDate(datetime.date):
        @classmethod
        def today(cls):
            return target_date

    monkeypatch.setattr(module, "date", PatchedDate)


def test_create_weekly_sp_market_id(monkeypatch):
    target = datetime.date(2024, 4, 9)  # Tuesday -> next Friday is 2024-04-12
    _patch_today(monkeypatch, shared.datetime, target)
    assert shared.create_weekly_sp_market_id() == "INXW-24APR12"


def test_create_weekly_nasdaq_market_id(monkeypatch):
    target = datetime.date(2024, 4, 9)  # Tuesday -> next Friday is 2024-04-12
    _patch_today(monkeypatch, shared.datetime, target)
    assert shared.create_weekly_nasdaq_market_id() == "NASDAQ100W-24APR12"


def test_get_next_sunday_regular_day():
    ref = datetime.date(2026, 2, 2)  # Monday
    assert shared.get_next_sunday(reference_date=ref) == "26FEB08".upper()


def test_get_next_sunday_on_sunday_skip(monkeypatch):
    ref = datetime.date(2026, 2, 8)  # Sunday
    assert shared.get_next_sunday(skip_today_if_sunday=True, reference_date=ref) == "26FEB15".upper()


def test_create_tsa_event_id():
    assert shared.create_tsa_event_id("26FEB08") == "KXTSAW-26FEB08"


def test_calculate_days_until_sunday_with_reference():
    ref = datetime.date(2026, 2, 2)  # Monday
    assert calculate_days_until_sunday(ref) == 6


def test_calculate_days_until_sunday_tuesday():
    ref = datetime.date(2026, 2, 3)  # Tuesday
    assert calculate_days_until_sunday(ref) == 5


def test_calculate_days_until_sunday_saturday():
    ref = datetime.date(2026, 2, 7)  # Saturday
    assert calculate_days_until_sunday(ref) == 1


def test_calculate_days_until_sunday_on_sunday_targets_next_week():
    ref = datetime.date(2026, 2, 8)  # Sunday
    assert calculate_days_until_sunday(ref) == 6


def test_get_same_date_last_year_day_of_week_adjusted():
    curr = datetime.datetime(2026, 2, 8)  # Sunday week 6
    expected = datetime.datetime.strptime("2025-02-09", "%Y-%m-%d")
    assert get_same_date_last_year_day_of_week_adjusted(curr) == expected
