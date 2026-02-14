"""Run entry-policy threshold sweeps for TSA backtests and select a gated policy.

The sweep evaluates many gate configurations over one fixed window, then applies
selection gates relative to a no-gate baseline:
- hold/improve ``pnl_total`` (within configured tolerance),
- reduce/hold ``max_drawdown``,
- preserve calibration quality via ``ece`` (within configured tolerance).
"""

from __future__ import annotations

import argparse
import datetime
import itertools
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from . import analyze_backtest_sanity
from . import backtest_tsa
from . import contract_probability_model
from .decision_policy import EntryPolicyConfig, evaluate_entry


DEFAULT_REPORT_ROOT = Path(__file__).resolve().parents[1] / "reports" / "experiments" / "tsa_policy_sweep"


def _parse_optional_float_grid(raw: str, *, default_none: bool = False) -> List[Optional[float]]:
    """Parse comma-separated floats with optional ``none``/``null`` sentinels.

    Examples:
    - ``"none,0.01,0.02" -> [None, 0.01, 0.02]``
    - ``"0.0,0.02" -> [0.0, 0.02]``
    """
    if not raw.strip():
        return [None] if default_none else [0.0]
    out: List[Optional[float]] = []
    for part in raw.split(","):
        token = part.strip().lower()
        if token in {"none", "null"}:
            out.append(None)
        else:
            out.append(float(token))
    return out


def _metrics_for_df(df: pd.DataFrame) -> Dict[str, float]:
    """Return key metrics for a backtest DataFrame (NaN-safe for empty input)."""
    if df.empty:
        return {
            "trades": 0.0,
            "pnl_total": 0.0,
            "max_drawdown": float("nan"),
            "ece": float("nan"),
        }
    calibration = analyze_backtest_sanity.calibration_table(df)
    metrics = analyze_backtest_sanity.key_metrics(df, calibration)
    return {
        "trades": float(metrics.get("trades", 0.0)),
        "pnl_total": float(metrics.get("pnl_total", 0.0)),
        "max_drawdown": float(metrics.get("max_drawdown", float("nan"))),
        "ece": float(metrics.get("ece", float("nan"))),
    }


def _build_policy_grid(
    min_edges: Iterable[Optional[float]],
    no_trade_bands: Iterable[float],
    max_side_prices: Iterable[Optional[float]],
    max_spreads: Iterable[Optional[float]],
) -> List[EntryPolicyConfig]:
    """Return cartesian product of policy configurations.

    Every value in each grid contributes to the full combination set.
    """
    grid: List[EntryPolicyConfig] = []
    for min_edge, no_trade_band, max_side_price, max_spread in itertools.product(
        min_edges,
        no_trade_bands,
        max_side_prices,
        max_spreads,
    ):
        grid.append(
            EntryPolicyConfig(
                min_edge=min_edge,
                no_trade_prob_band=float(no_trade_band),
                max_side_price=max_side_price,
                max_spread=max_spread,
            )
        )
    return grid


def _apply_policy_to_baseline_df(df: pd.DataFrame, policy: EntryPolicyConfig) -> pd.DataFrame:
    """Return subset of baseline rows that pass a given entry policy."""
    if df.empty:
        return df.copy()
    mask = df.apply(
        lambda row: evaluate_entry(
            policy,
            prob_yes=float(row["prob_yes"]),
            edge=float(row["edge"]),
            side_price=float(row["side_price"]),
            spread=(None if pd.isna(row["spread"]) else float(row["spread"])),
        ).allow_trade,
        axis=1,
    )
    return df[mask].reset_index(drop=True)


def _passes_gates(
    row: pd.Series,
    baseline: Dict[str, float],
    *,
    pnl_tolerance: float,
    ece_tolerance: float,
) -> bool:
    """Return True when a candidate satisfies baseline-relative selection gates."""
    pnl_gate = float(row["pnl_total"]) >= baseline["pnl_total"] - pnl_tolerance
    drawdown_gate = (
        np.isnan(baseline["max_drawdown"])
        or np.isnan(float(row["max_drawdown"]))
        or float(row["max_drawdown"]) <= baseline["max_drawdown"]
    )
    ece_gate = np.isnan(baseline["ece"]) or float(row["ece"]) <= baseline["ece"] + ece_tolerance
    return bool(pnl_gate and drawdown_gate and ece_gate)


def _select_policy(
    candidates: pd.DataFrame,
    baseline: Dict[str, float],
    *,
    pnl_tolerance: float,
    ece_tolerance: float,
) -> Optional[Dict[str, object]]:
    """Select the best policy among candidates that pass all gates.

    Ranking priority:
    1) higher ``pnl_total``
    2) lower ``max_drawdown``
    3) lower ``ece``
    """
    if candidates.empty:
        return None
    scored = candidates.copy()
    scored["passes_gates"] = scored.apply(
        lambda row: _passes_gates(
            row,
            baseline,
            pnl_tolerance=pnl_tolerance,
            ece_tolerance=ece_tolerance,
        ),
        axis=1,
    )
    passing = scored[scored["passes_gates"]]
    if passing.empty:
        return None
    ranked = passing.sort_values(
        by=["pnl_total", "max_drawdown", "ece"],
        ascending=[False, True, True],
        na_position="last",
    )
    return ranked.iloc[0].to_dict()


def _render_markdown(
    baseline: Dict[str, float],
    results: pd.DataFrame,
    selected: Optional[Dict[str, object]],
    run_id: str,
    args: argparse.Namespace,
) -> str:
    lines: List[str] = []
    lines.append("# TSA Policy Sweep")
    lines.append("")
    lines.append(f"- run_id: `{run_id}`")
    lines.append(f"- window: `{args.start} -> {args.end}`")
    lines.append(f"- prob_source: `{args.prob_source}`")
    lines.append(f"- pnl_tolerance: `{args.pnl_tolerance}`")
    lines.append(f"- ece_tolerance: `{args.ece_tolerance}`")
    lines.append("")
    lines.append("## Baseline (No Gates)")
    lines.append("")
    for key in ("trades", "pnl_total", "max_drawdown", "ece"):
        lines.append(f"- {key}: {baseline[key]}")
    lines.append("")
    lines.append("## Selected Policy")
    lines.append("")
    if selected is None:
        lines.append("- No policy passed all gates.")
    else:
        for key in (
            "min_edge",
            "no_trade_prob_band",
            "max_side_price",
            "max_spread",
            "trades",
            "pnl_total",
            "max_drawdown",
            "ece",
        ):
            lines.append(f"- {key}: {selected.get(key)}")
    lines.append("")
    lines.append("## Sweep Results")
    lines.append("")
    if results.empty:
        lines.append("_no rows_")
    else:
        cols = [
            "min_edge",
            "no_trade_prob_band",
            "max_side_price",
            "max_spread",
            "trades",
            "pnl_total",
            "max_drawdown",
            "ece",
            "passes_gates",
        ]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for _, row in results[cols].iterrows():
            cells = [str(row[col]) for col in cols]
            lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TSA entry-policy threshold sweep.")
    parser.add_argument("--start", required=True, help="Backtest start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Backtest end date YYYY-MM-DD")
    parser.add_argument("--interval", type=int, default=1440, help="Candlestick interval in minutes")
    parser.add_argument("--cache", type=Path, default=backtest_tsa.DEFAULT_CACHE, help="Backtest candle cache directory")
    parser.add_argument("--prob-source", choices=["model", "heuristic"], default="model", help="Probability source")
    parser.add_argument(
        "--model-bundle",
        type=Path,
        default=contract_probability_model.DEFAULT_MODEL_BUNDLE,
        help="Path to persisted model bundle",
    )
    parser.add_argument(
        "--min-edge-grid",
        default="none,0.01,0.02",
        help="Comma list of min-edge thresholds. Use 'none' to disable.",
    )
    parser.add_argument(
        "--no-trade-band-grid",
        default="0.0,0.01,0.02",
        help="Comma list of no-trade half-widths around 0.5 for P(YES).",
    )
    parser.add_argument(
        "--max-side-price-grid",
        default="none,0.75,0.80",
        help="Comma list of max-side-price filters. Use 'none' to disable.",
    )
    parser.add_argument(
        "--max-spread-grid",
        default="none,0.10,0.15",
        help="Comma list of max-spread filters. Use 'none' to disable.",
    )
    parser.add_argument("--pnl-tolerance", type=float, default=0.0, help="Allowable pnl_total shortfall vs baseline")
    parser.add_argument("--ece-tolerance", type=float, default=0.0, help="Allowable ECE increase vs baseline")
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT, help="Root directory for run outputs")
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint for policy sweep experiments."""
    args = _parse_args()
    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.report_root / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline_df = backtest_tsa.backtest_range(
        start_date=start_date,
        end_date=end_date,
        interval_minutes=args.interval,
        cache_dir=args.cache,
        prob_source=args.prob_source,
        model_bundle_path=args.model_bundle,
        entry_policy=EntryPolicyConfig(),
    )
    baseline_metrics = _metrics_for_df(baseline_df)

    grid = _build_policy_grid(
        min_edges=_parse_optional_float_grid(args.min_edge_grid, default_none=True),
        no_trade_bands=[float(v) for v in _parse_optional_float_grid(args.no_trade_band_grid)],
        max_side_prices=_parse_optional_float_grid(args.max_side_price_grid, default_none=True),
        max_spreads=_parse_optional_float_grid(args.max_spread_grid, default_none=True),
    )

    rows: List[Dict[str, object]] = []
    for policy in grid:
        df = _apply_policy_to_baseline_df(baseline_df, policy)
        metrics = _metrics_for_df(df)
        row: Dict[str, object] = asdict(policy)
        row.update(metrics)
        rows.append(row)

    results = pd.DataFrame(rows)
    if not results.empty:
        results["passes_gates"] = results.apply(
            lambda row: _passes_gates(
                row,
                baseline_metrics,
                pnl_tolerance=args.pnl_tolerance,
                ece_tolerance=args.ece_tolerance,
            ),
            axis=1,
        )
        results = results.sort_values(
            by=["passes_gates", "pnl_total", "max_drawdown", "ece"],
            ascending=[False, False, True, True],
            na_position="last",
        )

    selected = _select_policy(
        results,
        baseline_metrics,
        pnl_tolerance=args.pnl_tolerance,
        ece_tolerance=args.ece_tolerance,
    )

    csv_path = out_dir / "policy_sweep_results.csv"
    md_path = out_dir / "policy_sweep_summary.md"
    meta_path = out_dir / "policy_sweep_metadata.json"
    results.to_csv(csv_path, index=False)
    md_path.write_text(_render_markdown(baseline_metrics, results, selected, run_id, args))
    meta_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "baseline": baseline_metrics,
                "selected_policy": selected,
                "args": {
                    "start": args.start,
                    "end": args.end,
                    "interval": args.interval,
                    "prob_source": args.prob_source,
                    "min_edge_grid": args.min_edge_grid,
                    "no_trade_band_grid": args.no_trade_band_grid,
                    "max_side_price_grid": args.max_side_price_grid,
                    "max_spread_grid": args.max_spread_grid,
                    "pnl_tolerance": args.pnl_tolerance,
                    "ece_tolerance": args.ece_tolerance,
                },
                "artifacts": {
                    "results_csv": str(csv_path.resolve()),
                    "summary_md": str(md_path.resolve()),
                },
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )

    print(f"[policy_sweep] run_dir: {out_dir}")
    print(f"[policy_sweep] results_csv: {csv_path}")
    print(f"[policy_sweep] summary_md: {md_path}")


if __name__ == "__main__":
    main()
