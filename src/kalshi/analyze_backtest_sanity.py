"""Sanity checks and diagnostics for TSA backtest output CSVs."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


DEFAULT_REPORTS = Path(__file__).resolve().parents[1] / "reports"
EPS = 1e-9


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run sanity checks on TSA backtest results.")
    parser.add_argument("--csv", type=Path, required=True, help="Path to backtest CSV")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_REPORTS, help="Directory for markdown report")
    parser.add_argument("--metadata-json", type=Path, default=None, help="Optional path to write run metadata JSON")
    return parser.parse_args()


def _required_columns() -> List[str]:
    return [
        "market",
        "date",
        "side",
        "prob",
        "fill_price",
        "outcome",
        "pnl",
        "brier",
        "logloss",
        "edge",
    ]


def _bounded_series_check(series: pd.Series, lower: float, upper: float) -> Tuple[bool, str]:
    below = int((series < lower).sum())
    above = int((series > upper).sum())
    passed = below == 0 and above == 0
    return passed, f"below={below}, above={above}, bounds=[{lower}, {upper}]"


def _formula_deltas(df: pd.DataFrame) -> Dict[str, pd.Series]:
    contract_price = np.where(df["side"] == "yes", df["fill_price"], 1 - df["fill_price"])
    expected_pnl = np.where(df["outcome"] == 1, 1 - contract_price, -contract_price)
    expected_brier = (df["prob"] - df["outcome"]) ** 2
    prob_clipped = np.clip(df["prob"], EPS, 1 - EPS)
    expected_logloss = -(df["outcome"] * np.log(prob_clipped) + (1 - df["outcome"]) * np.log(1 - prob_clipped))
    expected_edge = df["prob"] - contract_price
    return {
        "pnl_abs_delta": np.abs(df["pnl"] - expected_pnl),
        "brier_abs_delta": np.abs(df["brier"] - expected_brier),
        "logloss_abs_delta": np.abs(df["logloss"] - expected_logloss),
        "edge_abs_delta": np.abs(df["edge"] - expected_edge),
    }


def run_checks(df: pd.DataFrame) -> List[CheckResult]:
    checks: List[CheckResult] = []
    required = _required_columns()
    missing = [col for col in required if col not in df.columns]
    checks.append(
        CheckResult(
            "required_columns",
            len(missing) == 0,
            "missing=" + (",".join(missing) if missing else "none"),
        )
    )
    if missing:
        return checks

    bounds_ok, bounds_details = _bounded_series_check(df["prob"], 0.0, 1.0)
    checks.append(CheckResult("prob_in_[0,1]", bounds_ok, bounds_details))

    fill_ok, fill_details = _bounded_series_check(df["fill_price"], 0.0, 1.0)
    checks.append(CheckResult("fill_price_in_[0,1]", fill_ok, fill_details))

    valid_sides = int((~df["side"].isin(["yes", "no"])).sum())
    checks.append(CheckResult("side_is_yes_or_no", valid_sides == 0, f"invalid_rows={valid_sides}"))

    valid_outcomes = int((~df["outcome"].isin([0, 1])).sum())
    checks.append(CheckResult("outcome_is_binary", valid_outcomes == 0, f"invalid_rows={valid_outcomes}"))

    duplicate_rows = int(df.duplicated(subset=["market", "date"]).sum())
    checks.append(CheckResult("no_duplicate_market_date_rows", duplicate_rows == 0, f"duplicates={duplicate_rows}"))

    deltas = _formula_deltas(df)
    for metric_name, delta in deltas.items():
        max_delta = float(delta.max()) if len(delta) else 0.0
        bad_rows = int((delta > 1e-8).sum())
        checks.append(
            CheckResult(
                metric_name,
                bad_rows == 0,
                f"max_delta={max_delta:.12g}, rows_over_tolerance={bad_rows}",
            )
        )

    return checks


def calibration_table(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    framed = df.assign(confidence=df["prob"])
    framed["bin"] = pd.cut(framed["confidence"], bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    grouped = framed.groupby("bin", observed=False)
    table = grouped.agg(
        trades=("outcome", "size"),
        mean_confidence=("confidence", "mean"),
        hit_rate=("outcome", "mean"),
        avg_pnl=("pnl", "mean"),
    ).reset_index()
    table["calibration_gap"] = table["hit_rate"] - table["mean_confidence"]
    return table


def expected_calibration_error(calibration: pd.DataFrame) -> float:
    """Return weighted absolute calibration gap across populated bins."""
    populated = calibration[calibration["trades"] > 0]
    if populated.empty:
        return float("nan")
    total_trades = populated["trades"].sum()
    abs_gap = (populated["hit_rate"] - populated["mean_confidence"]).abs()
    return float((populated["trades"] * abs_gap).sum() / total_trades)


def max_drawdown(df: pd.DataFrame) -> float:
    """Return maximum drawdown from cumulative PnL."""
    if df.empty:
        return float("nan")
    cumulative = df["pnl"].cumsum()
    running_peak = cumulative.cummax()
    drawdowns = running_peak - cumulative
    return float(drawdowns.max())


def _sort_for_time_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Sort rows by date if parseable, preserving stable order for ties."""
    if "date" not in df.columns:
        return df.reset_index(drop=True)
    sorted_df = df.copy()
    sorted_df["__parsed_date"] = pd.to_datetime(sorted_df["date"], errors="coerce")
    sorted_df["__row"] = np.arange(len(sorted_df))
    sorted_df = sorted_df.sort_values(by=["__parsed_date", "__row"], kind="mergesort")
    return sorted_df.drop(columns=["__parsed_date", "__row"]).reset_index(drop=True)


def key_metrics(df: pd.DataFrame, calibration: pd.DataFrame) -> Dict[str, float]:
    """Return canonical KPI set used for baseline/candidate comparisons."""
    if df.empty:
        return {}
    sorted_df = _sort_for_time_metrics(df)
    pnl_std = float(sorted_df["pnl"].std(ddof=0))
    pnl_avg = float(sorted_df["pnl"].mean())
    sharpe_like = pnl_avg / pnl_std if pnl_std > 0 else float("nan")
    return {
        "trades": float(len(sorted_df)),
        "pnl_total": float(sorted_df["pnl"].sum()),
        "pnl_avg": pnl_avg,
        "pnl_std": pnl_std,
        "sharpe_like": float(sharpe_like),
        "max_drawdown": max_drawdown(sorted_df),
        "hit_rate": float(sorted_df["outcome"].mean()),
        "avg_edge": float(sorted_df["edge"].mean()),
        "edge_pnl_corr": float(sorted_df["edge"].corr(sorted_df["pnl"])) if len(sorted_df) > 1 else float("nan"),
        "brier_mean": float(sorted_df["brier"].mean()),
        "logloss_mean": float(sorted_df["logloss"].mean()),
        "ece": expected_calibration_error(calibration),
    }


def edge_diagnostics(df: pd.DataFrame) -> Dict[str, float]:
    edge_positive = df[df["edge"] > 0]
    edge_non_positive = df[df["edge"] <= 0]

    def _safe_mean(frame: pd.DataFrame, col: str) -> float:
        if frame.empty:
            return float("nan")
        return float(frame[col].mean())

    return {
        "n_edge_positive": float(len(edge_positive)),
        "n_edge_non_positive": float(len(edge_non_positive)),
        "corr_edge_pnl": float(df["edge"].corr(df["pnl"])) if len(df) > 1 else float("nan"),
        "mean_pnl_edge_positive": _safe_mean(edge_positive, "pnl"),
        "mean_pnl_edge_non_positive": _safe_mean(edge_non_positive, "pnl"),
        "hit_rate_edge_positive": _safe_mean(edge_positive, "outcome"),
        "hit_rate_edge_non_positive": _safe_mean(edge_non_positive, "outcome"),
    }


def bootstrap_mean_pnl_ci(df: pd.DataFrame, n_boot: int = 2000, seed: int = 7) -> Tuple[float, float]:
    if df.empty:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    pnl = df["pnl"].to_numpy()
    n = len(pnl)
    samples = rng.choice(pnl, size=(n_boot, n), replace=True)
    boot_means = samples.mean(axis=1)
    return float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))


def summary_by_side(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("side", observed=False)
        .agg(
            trades=("market", "size"),
            hit_rate=("outcome", "mean"),
            avg_prob=("prob", "mean"),
            avg_fill_price=("fill_price", "mean"),
            avg_edge=("edge", "mean"),
            avg_pnl=("pnl", "mean"),
            pnl_total=("pnl", "sum"),
        )
        .reset_index()
    )


def render_markdown(
    csv_path: Path,
    checks: List[CheckResult],
    df: pd.DataFrame,
    by_side: pd.DataFrame,
    calibration: pd.DataFrame,
    edge_stats: Dict[str, float],
    pnl_ci: Tuple[float, float],
    metrics: Dict[str, float],
) -> str:
    pass_count = sum(1 for c in checks if c.passed)
    lines: List[str] = []
    lines.append("# TSA Backtest Sanity Report")
    lines.append("")
    lines.append(f"- source_csv: `{csv_path}`")
    lines.append(f"- generated_at: {datetime.datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- trades: {len(df)}")
    lines.append(f"- checks_passed: {pass_count}/{len(checks)}")
    lines.append("")
    lines.append("## Invariant Checks")
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"- [{status}] {check.name}: {check.details}")
    lines.append("")
    lines.append("## Key Metrics")
    lines.append(f"- pnl_total: {metrics['pnl_total']:.6f}")
    lines.append(f"- pnl_avg: {metrics['pnl_avg']:.6f}")
    lines.append(f"- pnl_std: {metrics['pnl_std']:.6f}")
    lines.append(f"- sharpe_like: {metrics['sharpe_like']:.6f}")
    lines.append(f"- max_drawdown: {metrics['max_drawdown']:.6f}")
    lines.append(f"- hit_rate: {metrics['hit_rate']:.6f}")
    lines.append(f"- avg_edge: {metrics['avg_edge']:.6f}")
    lines.append(f"- edge_pnl_corr: {metrics['edge_pnl_corr']:.6f}")
    lines.append(f"- brier_mean: {metrics['brier_mean']:.6f}")
    lines.append(f"- logloss_mean: {metrics['logloss_mean']:.6f}")
    lines.append(f"- ece: {metrics['ece']:.6f}")
    lines.append(f"- pnl_avg_95pct_bootstrap_ci: [{pnl_ci[0]:.6f}, {pnl_ci[1]:.6f}]")
    lines.append("")
    lines.append("## Edge Diagnostics")
    for key, value in edge_stats.items():
        if key.startswith("n_") and np.isfinite(value):
            lines.append(f"- {key}: {int(value)}")
        else:
            lines.append(f"- {key}: {value:.6f}")
    lines.append("")
    lines.append("## By Side")
    lines.append(_df_to_markdown(by_side))
    lines.append("")
    lines.append("## Calibration (confidence bins)")
    lines.append(_df_to_markdown(calibration))
    lines.append("")
    return "\n".join(lines)


def build_run_metadata(
    csv_path: Path,
    metrics: Dict[str, float],
    checks: List[CheckResult],
) -> Dict[str, object]:
    """Return reproducibility metadata for this analyzer run."""
    generated_at = datetime.datetime.now().isoformat(timespec="seconds")
    content = csv_path.read_bytes()
    csv_sha256 = hashlib.sha256(content).hexdigest()
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        git_commit = None
    return {
        "generated_at": generated_at,
        "source_csv": str(csv_path.resolve()),
        "source_csv_sha256": csv_sha256,
        "git_commit": git_commit,
        "python_version": sys.version.split()[0],
        "checks_passed": int(sum(1 for c in checks if c.passed)),
        "checks_total": int(len(checks)),
        "metrics": metrics,
        "command": " ".join(sys.argv),
    }


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


def main() -> None:
    args = _parse_args()
    df = pd.read_csv(args.csv)
    checks = run_checks(df)
    by_side = summary_by_side(df)
    calibration = calibration_table(df)
    metrics = key_metrics(df, calibration)
    edge_stats = edge_diagnostics(df)
    pnl_ci = bootstrap_mean_pnl_ci(df)

    report = render_markdown(
        csv_path=args.csv,
        checks=checks,
        df=df,
        by_side=by_side,
        calibration=calibration,
        edge_stats=edge_stats,
        pnl_ci=pnl_ci,
        metrics=metrics,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.csv.stem.replace("tsa_backtest_", "tsa_backtest_sanity_")
    out_path = args.out_dir / f"{stem}.md"
    out_path.write_text(report)
    metadata = build_run_metadata(args.csv, metrics=metrics, checks=checks)
    metadata_path = args.metadata_json or (args.out_dir / f"{stem}.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))
    print(out_path)


if __name__ == "__main__":
    main()
