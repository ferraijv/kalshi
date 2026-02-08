"""Compare candidate backtest output against a baseline CSV."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from . import analyze_backtest_sanity


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline and candidate TSA backtests.")
    parser.add_argument("--baseline", type=Path, required=True, help="Path to baseline backtest CSV")
    parser.add_argument("--candidate", type=Path, required=True, help="Path to candidate backtest CSV")
    parser.add_argument("--out", type=Path, default=None, help="Optional markdown output path")
    return parser.parse_args()


def _metrics_for_csv(path: Path) -> Dict[str, float]:
    df = pd.read_csv(path)
    calibration = analyze_backtest_sanity.calibration_table(df)
    return analyze_backtest_sanity.key_metrics(df, calibration)


def compare_metrics(baseline: Dict[str, float], candidate: Dict[str, float]) -> pd.DataFrame:
    """Return side-by-side KPI comparison with absolute and percent deltas."""
    rows: List[Dict[str, float]] = []
    for metric in sorted(set(baseline.keys()) | set(candidate.keys())):
        base = baseline.get(metric, float("nan"))
        cand = candidate.get(metric, float("nan"))
        delta_abs = cand - base
        if base == 0 or not np.isfinite(base):
            delta_pct = float("nan")
        else:
            delta_pct = (delta_abs / abs(base)) * 100
        rows.append(
            {
                "metric": metric,
                "baseline": base,
                "candidate": cand,
                "delta_abs": delta_abs,
                "delta_pct": delta_pct,
            }
        )
    return pd.DataFrame(rows)


def _format_cell(value: object) -> str:
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.6f}"
    return str(value)


def _df_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_no rows_"
    headers = [str(col) for col in df.columns]
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        cells = [_format_cell(row[col]) for col in df.columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_markdown(baseline_path: Path, candidate_path: Path, comparison: pd.DataFrame) -> str:
    """Render a markdown report for a baseline/candidate comparison."""
    lines = [
        "# TSA Backtest Comparison",
        "",
        f"- baseline_csv: `{baseline_path.resolve()}`",
        f"- candidate_csv: `{candidate_path.resolve()}`",
        "",
        "## KPI Delta Table",
        _df_to_markdown(comparison),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = _parse_args()
    baseline_metrics = _metrics_for_csv(args.baseline)
    candidate_metrics = _metrics_for_csv(args.candidate)
    comparison = compare_metrics(baseline_metrics, candidate_metrics)
    report = render_markdown(args.baseline, args.candidate, comparison)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report)
    print(report)


if __name__ == "__main__":
    main()
