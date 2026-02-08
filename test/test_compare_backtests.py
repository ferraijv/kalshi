import numpy as np
import pytest

from src.kalshi import compare_backtests


def test_compare_metrics_computes_absolute_and_percent_delta():
    baseline = {"pnl_total": 10.0, "hit_rate": 0.5}
    candidate = {"pnl_total": 12.5, "hit_rate": 0.4}
    comparison = compare_backtests.compare_metrics(baseline, candidate).set_index("metric")

    assert comparison.loc["pnl_total", "delta_abs"] == 2.5
    assert comparison.loc["pnl_total", "delta_pct"] == 25.0
    assert comparison.loc["hit_rate", "delta_abs"] == pytest.approx(-0.1)
    assert comparison.loc["hit_rate", "delta_pct"] == pytest.approx(-20.0)


def test_compare_metrics_handles_zero_baseline_without_pct():
    baseline = {"pnl_total": 0.0}
    candidate = {"pnl_total": 1.0}
    comparison = compare_backtests.compare_metrics(baseline, candidate)
    row = comparison[comparison["metric"] == "pnl_total"].iloc[0]

    assert row["delta_abs"] == 1.0
    assert not np.isfinite(row["delta_pct"])
