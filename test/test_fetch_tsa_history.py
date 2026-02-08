from pathlib import Path

from src.kalshi import fetch_tsa_history


def test_cache_path_is_stable_for_identical_request():
    cache_dir = Path("/tmp/cache")
    first = fetch_tsa_history._cache_path_for_request(
        cache_dir=cache_dir,
        market_ticker="KXTSAW-26FEB08-A2.35",
        interval_minutes=1440,
        start_ts=1738454400,
        end_ts=1739059200,
        include_latest_before_start=False,
    )
    second = fetch_tsa_history._cache_path_for_request(
        cache_dir=cache_dir,
        market_ticker="KXTSAW-26FEB08-A2.35",
        interval_minutes=1440,
        start_ts=1738454400,
        end_ts=1739059200,
        include_latest_before_start=False,
    )

    assert first == second


def test_cache_path_changes_for_different_windows_and_flags():
    cache_dir = Path("/tmp/cache")
    base = fetch_tsa_history._cache_path_for_request(
        cache_dir=cache_dir,
        market_ticker="KXTSAW-26FEB08-A2.35",
        interval_minutes=1440,
        start_ts=1738454400,
        end_ts=1739059200,
        include_latest_before_start=False,
    )
    changed_window = fetch_tsa_history._cache_path_for_request(
        cache_dir=cache_dir,
        market_ticker="KXTSAW-26FEB08-A2.35",
        interval_minutes=1440,
        start_ts=1738454401,
        end_ts=1739059200,
        include_latest_before_start=False,
    )
    changed_flag = fetch_tsa_history._cache_path_for_request(
        cache_dir=cache_dir,
        market_ticker="KXTSAW-26FEB08-A2.35",
        interval_minutes=1440,
        start_ts=1738454400,
        end_ts=1739059200,
        include_latest_before_start=True,
    )

    assert base != changed_window
    assert base != changed_flag

