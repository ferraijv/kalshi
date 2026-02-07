"""Sanity checks and diagnostics for TSA backtest output CSVs."""

from __future__ import annotations

import argparse
import datetime
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
    lines.append(f"- pnl_total: {df['pnl'].sum():.6f}")
    lines.append(f"- pnl_avg: {df['pnl'].mean():.6f}")
    lines.append(f"- hit_rate: {df['outcome'].mean():.6f}")
    lines.append(f"- avg_edge: {df['edge'].mean():.6f}")
    lines.append(f"- brier_mean: {df['brier'].mean():.6f}")
    lines.append(f"- logloss_mean: {df['logloss'].mean():.6f}")
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
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.csv.stem.replace("tsa_backtest_", "tsa_backtest_sanity_")
    out_path = args.out_dir / f"{stem}.md"
    out_path.write_text(report)
    print(out_path)


if __name__ == "__main__":
    main()
