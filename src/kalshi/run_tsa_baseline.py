"""Run baseline TSA backtest pipeline from config and emit reproducible artifacts."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from . import analyze_backtest_sanity
from . import backtest_tsa
from . import compare_backtests


DEFAULT_CONFIG = Path(__file__).resolve().parent / "configs" / "tsa_backtest_baseline.json"


def _sha256(path: Path) -> str:
    """Return SHA-256 hex digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_config(path: Path) -> Dict[str, object]:
    """Read baseline config JSON from disk."""
    return json.loads(path.read_text())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline TSA backtest pipeline from config.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Path to baseline JSON config")
    parser.add_argument("--baseline-csv", type=Path, default=None, help="Optional baseline CSV for KPI comparison")
    return parser.parse_args()


def _write_backtest_artifacts(df: pd.DataFrame, report_dir: Path, timestamp: str) -> Dict[str, Path]:
    """Write backtest CSV and summary markdown with a shared timestamp suffix."""
    report_dir.mkdir(parents=True, exist_ok=True)
    csv_path = report_dir / f"tsa_backtest_{timestamp}.csv"
    md_path = report_dir / f"tsa_backtest_{timestamp}.md"
    df.to_csv(csv_path, index=False)
    summary = backtest_tsa.summarize(df)
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("# TSA Backtest\n\n")
        for key, value in summary.items():
            handle.write(f"- {key}: {value}\n")
    return {"csv": csv_path, "summary_md": md_path}


def _write_sanity_artifacts(csv_path: Path, report_dir: Path, timestamp: str) -> Dict[str, Path]:
    """Write sanity markdown and metadata JSON using analyzer internals."""
    df = pd.read_csv(csv_path)
    checks = analyze_backtest_sanity.run_checks(df)
    by_side = analyze_backtest_sanity.summary_by_side(df)
    calibration = analyze_backtest_sanity.calibration_table(df)
    metrics = analyze_backtest_sanity.key_metrics(df, calibration)
    edge_stats = analyze_backtest_sanity.edge_diagnostics(df)
    pnl_ci = analyze_backtest_sanity.bootstrap_mean_pnl_ci(df)

    sanity_md = report_dir / f"tsa_backtest_sanity_{timestamp}.md"
    sanity_json = report_dir / f"tsa_backtest_sanity_{timestamp}.json"
    markdown = analyze_backtest_sanity.render_markdown(
        csv_path=csv_path,
        checks=checks,
        df=df,
        by_side=by_side,
        calibration=calibration,
        edge_stats=edge_stats,
        pnl_ci=pnl_ci,
        metrics=metrics,
    )
    sanity_md.write_text(markdown)
    metadata = analyze_backtest_sanity.build_run_metadata(csv_path, metrics=metrics, checks=checks)
    sanity_json.write_text(json.dumps(metadata, indent=2, sort_keys=True))
    return {"sanity_md": sanity_md, "sanity_json": sanity_json}


def run_from_config(config_path: Path, baseline_csv: Optional[Path] = None) -> Dict[str, str]:
    """Run configured baseline backtest and return written artifact paths."""
    cfg = _load_config(config_path)
    backtest_cfg = cfg["backtest"]
    report_dir = Path(cfg["reporting"]["report_dir"])
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    df = backtest_tsa.backtest_range(
        start_date=datetime.date.fromisoformat(backtest_cfg["start"]),
        end_date=datetime.date.fromisoformat(backtest_cfg["end"]),
        interval_minutes=int(backtest_cfg.get("interval_minutes", 1440)),
        include_latest_before_start=bool(backtest_cfg.get("include_latest_before_start", False)),
    )

    paths = _write_backtest_artifacts(df=df, report_dir=report_dir, timestamp=timestamp)
    paths.update(_write_sanity_artifacts(csv_path=paths["csv"], report_dir=report_dir, timestamp=timestamp))

    comparison_md = None
    if baseline_csv:
        baseline_metrics = compare_backtests._metrics_for_csv(baseline_csv)
        candidate_metrics = compare_backtests._metrics_for_csv(paths["csv"])
        comparison = compare_backtests.compare_metrics(baseline_metrics, candidate_metrics)
        comparison_md = report_dir / f"tsa_backtest_comparison_{timestamp}.md"
        comparison_md.write_text(compare_backtests.render_markdown(baseline_csv, paths["csv"], comparison))

    run_metadata = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "config_path": str(config_path.resolve()),
        "config_sha256": _sha256(config_path),
        "artifacts": {name: str(path.resolve()) for name, path in paths.items()},
        "comparison_md": str(comparison_md.resolve()) if comparison_md else None,
    }
    run_meta_path = report_dir / f"tsa_baseline_run_{timestamp}.json"
    run_meta_path.write_text(json.dumps(run_metadata, indent=2, sort_keys=True))
    run_metadata["run_metadata_json"] = str(run_meta_path.resolve())
    return run_metadata


def main() -> None:
    args = _parse_args()
    output = run_from_config(config_path=args.config, baseline_csv=args.baseline_csv)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
