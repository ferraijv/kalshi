import json
from pathlib import Path

import pandas as pd

from src.kalshi import run_tsa_baseline


def _sample_backtest_df() -> pd.DataFrame:
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
                "logloss": 0.3566749439,
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
                "logloss": 0.2231435513,
                "edge": 0.1,
            },
        ]
    )


def test_run_from_config_writes_pipeline_artifacts(monkeypatch, tmp_path):
    config_path = tmp_path / "baseline.json"
    report_dir = tmp_path / "reports"
    config_path.write_text(
        json.dumps(
            {
                "backtest": {
                    "start": "2025-12-01",
                    "end": "2025-12-31",
                    "interval_minutes": 1440,
                    "include_latest_before_start": False,
                },
                "reporting": {"report_dir": str(report_dir)},
            }
        )
    )
    monkeypatch.setattr(run_tsa_baseline.backtest_tsa, "backtest_range", lambda **_kwargs: _sample_backtest_df())

    output = run_tsa_baseline.run_from_config(config_path=config_path)

    artifacts = output["artifacts"]
    assert Path(artifacts["csv"]).exists()
    assert Path(artifacts["summary_md"]).exists()
    assert Path(artifacts["sanity_md"]).exists()
    assert Path(artifacts["sanity_json"]).exists()
    assert output["comparison_md"] is None
    assert Path(output["run_metadata_json"]).exists()


def test_run_from_config_writes_comparison_when_baseline_provided(monkeypatch, tmp_path):
    config_path = tmp_path / "baseline.json"
    report_dir = tmp_path / "reports"
    config_path.write_text(
        json.dumps(
            {
                "backtest": {
                    "start": "2025-12-01",
                    "end": "2025-12-31",
                    "interval_minutes": 1440,
                    "include_latest_before_start": False,
                },
                "reporting": {"report_dir": str(report_dir)},
            }
        )
    )
    monkeypatch.setattr(run_tsa_baseline.backtest_tsa, "backtest_range", lambda **_kwargs: _sample_backtest_df())

    baseline_csv = tmp_path / "baseline_input.csv"
    _sample_backtest_df().to_csv(baseline_csv, index=False)
    output = run_tsa_baseline.run_from_config(config_path=config_path, baseline_csv=baseline_csv)

    assert output["comparison_md"] is not None
    assert Path(output["comparison_md"]).exists()
