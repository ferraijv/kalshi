import numpy as np
import pandas as pd

from src.kalshi import analyze_backtest_sanity


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "market": "KXTSAW-25DEC07-A2.45",
                "date": "2025-12-07",
                "side": "yes",
                "prob": 0.7,
                "fill_price": 0.6,
                "outcome": 1,
                "pnl": 0.4,
                "brier": 0.09,
                "logloss": -np.log(0.7),
                "edge": 0.1,
            },
            {
                "market": "KXTSAW-25DEC14-A2.45",
                "date": "2025-12-14",
                "side": "no",
                "prob": 0.8,
                "fill_price": 0.3,
                "outcome": 1,
                "pnl": 0.3,
                "brier": 0.04,
                "logloss": -np.log(0.8),
                "edge": 0.1,
            },
        ]
    )


def test_run_checks_passes_for_consistent_rows():
    df = _sample_df()
    checks = analyze_backtest_sanity.run_checks(df)
    assert checks
    assert all(check.passed for check in checks)


def test_run_checks_detects_formula_breakage():
    df = _sample_df()
    df.loc[0, "pnl"] = 0.1
    checks = analyze_backtest_sanity.run_checks(df)
    mapped = {check.name: check for check in checks}
    assert not mapped["pnl_abs_delta"].passed


def test_calibration_uses_side_probability_directly():
    df = pd.DataFrame(
        [
            {
                "market": "KXTSAW-25DEC14-A2.45",
                "date": "2025-12-14",
                "side": "no",
                "prob": 0.8,
                "fill_price": 0.3,
                "outcome": 1,
                "pnl": 0.3,
                "brier": 0.04,
                "logloss": -np.log(0.8),
                "edge": 0.1,
            }
        ]
    )
    table = analyze_backtest_sanity.calibration_table(df, bins=10)
    populated = table[table["trades"] > 0].iloc[0]
    assert 0.7 <= populated["mean_confidence"] <= 0.9


def test_key_metrics_includes_drawdown_and_ece():
    df = pd.DataFrame(
        [
            {
                "market": "KXTSAW-25DEC07-A2.45",
                "date": "2025-12-07",
                "side": "yes",
                "prob": 0.7,
                "fill_price": 0.6,
                "outcome": 1,
                "pnl": 0.4,
                "brier": 0.09,
                "logloss": -np.log(0.7),
                "edge": 0.1,
            },
            {
                "market": "KXTSAW-25DEC14-A2.45",
                "date": "2025-12-14",
                "side": "yes",
                "prob": 0.8,
                "fill_price": 0.6,
                "outcome": 0,
                "pnl": -0.6,
                "brier": 0.64,
                "logloss": -np.log(0.2),
                "edge": 0.2,
            },
            {
                "market": "KXTSAW-25DEC21-A2.45",
                "date": "2025-12-21",
                "side": "yes",
                "prob": 0.6,
                "fill_price": 0.5,
                "outcome": 1,
                "pnl": 0.5,
                "brier": 0.16,
                "logloss": -np.log(0.6),
                "edge": 0.1,
            },
        ]
    )
    calibration = analyze_backtest_sanity.calibration_table(df, bins=10)
    metrics = analyze_backtest_sanity.key_metrics(df, calibration)

    assert metrics["trades"] == 3
    assert metrics["max_drawdown"] == 0.6
    assert 0.0 <= metrics["ece"] <= 1.0
    assert np.isfinite(metrics["pnl_std"])
