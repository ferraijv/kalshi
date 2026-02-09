"""Run feature-set ablations for TSA yes-probability modeling."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Dict, List, Sequence

import pandas as pd

from . import backtest_tsa
from . import train_tsa_probability_model


DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "data" / "datasets" / "tsa_contract_dataset.csv"
DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "experiments" / "tsa_feature_ablation"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "data" / "models" / "ablation"


def _default_feature_sets() -> Dict[str, List[str]]:
    """Return named feature sets for ablation experiments."""
    return {
        "full": [
            "floor_strike_millions",
            "strike_distance_pct",
            "abs_strike_distance_pct",
            "days_until_sunday",
            "day_1_trend",
            "day_7_trend",
            "yoy_adjustment",
            "last_year_passengers",
        ],
        "lean_core": [
            "strike_distance_pct",
            "abs_strike_distance_pct",
            "day_7_trend",
        ],
        "lean_plus_strike_level": [
            "strike_distance_pct",
            "abs_strike_distance_pct",
            "day_7_trend",
            "floor_strike_millions",
        ],
        "lean_plus_last_year": [
            "strike_distance_pct",
            "abs_strike_distance_pct",
            "day_7_trend",
            "last_year_passengers",
        ],
        "no_composite_yoy": [
            "floor_strike_millions",
            "strike_distance_pct",
            "abs_strike_distance_pct",
            "day_1_trend",
            "day_7_trend",
            "last_year_passengers",
        ],
        "without_days_until_sunday": [
            "floor_strike_millions",
            "strike_distance_pct",
            "abs_strike_distance_pct",
            "day_1_trend",
            "day_7_trend",
            "yoy_adjustment",
            "last_year_passengers",
        ],
    }


def _parse_feature_sets(raw: str | None) -> Dict[str, List[str]]:
    """Parse optional JSON file of feature sets; otherwise use defaults."""
    if raw is None:
        return _default_feature_sets()
    payload = json.loads(Path(raw).read_text())
    if not isinstance(payload, dict):
        raise ValueError("Feature-set JSON must be an object: {name: [features...]}.")
    out: Dict[str, List[str]] = {}
    for name, features in payload.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Feature-set names must be non-empty strings.")
        if not isinstance(features, list) or not features:
            raise ValueError(f"Feature set '{name}' must be a non-empty list.")
        out[name] = [str(v) for v in features]
    return out


def _render_markdown(
    rows: pd.DataFrame,
    run_ts: str,
    dataset_csv: Path,
    start_date: datetime.date,
    end_date: datetime.date,
    train_weeks: int,
    val_weeks: int,
    step_weeks: int,
    did_backtest: bool,
) -> str:
    lines: List[str] = []
    lines.append("# TSA Feature Ablation")
    lines.append("")
    lines.append(f"- generated_at: `{run_ts}`")
    lines.append(f"- dataset_csv: `{dataset_csv.resolve()}`")
    lines.append(f"- backtest_window: `{start_date.isoformat()} -> {end_date.isoformat()}`")
    lines.append(f"- walk_forward: `train_weeks={train_weeks}, val_weeks={val_weeks}, step_weeks={step_weeks}`")
    lines.append(f"- backtest_ran: `{did_backtest}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    if rows.empty:
        lines.append("_no rows_")
        return "\n".join(lines)

    cols = [
        "name",
        "num_features",
        "oos_brier",
        "oos_logloss",
        "oos_auc",
        "backtest_pnl_total",
        "backtest_pnl_avg",
        "backtest_hit_rate_proxy",
        "backtest_brier",
        "backtest_logloss",
        "features",
    ]
    show = rows[cols].copy()
    header = "| " + " | ".join(cols) + " |"
    divider = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines.append(header)
    lines.append(divider)
    for _, row in show.iterrows():
        cells = [str(row[c]) for c in cols]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def _run_single_variant(
    name: str,
    features: Sequence[str],
    dataset_csv: Path,
    model_dir: Path,
    train_weeks: int,
    val_weeks: int,
    step_weeks: int,
    run_backtest: bool,
    start_date: datetime.date,
    end_date: datetime.date,
    interval_minutes: int,
    cache_dir: Path,
) -> Dict[str, object]:
    model_path = model_dir / f"tsa_yes_probability_model_{name}.joblib"
    metadata_path = model_path.with_suffix(".metadata.json")
    metadata = train_tsa_probability_model.train_from_dataset(
        dataset_csv=dataset_csv,
        feature_columns=list(features),
        train_weeks=train_weeks,
        val_weeks=val_weeks,
        step_weeks=step_weeks,
        out_model=model_path,
        out_metadata=metadata_path,
    )

    row: Dict[str, object] = {
        "name": name,
        "num_features": len(features),
        "features": ",".join(features),
        "model_path": str(model_path.resolve()),
        "metadata_path": str(metadata_path.resolve()),
        "oos_brier": metadata["aggregate_oos_metrics"]["brier"],
        "oos_logloss": metadata["aggregate_oos_metrics"]["logloss"],
        "oos_auc": metadata["aggregate_oos_metrics"]["auc"],
        "backtest_pnl_total": None,
        "backtest_pnl_avg": None,
        "backtest_hit_rate_proxy": None,
        "backtest_brier": None,
        "backtest_logloss": None,
    }
    if run_backtest:
        df = backtest_tsa.backtest_range(
            start_date=start_date,
            end_date=end_date,
            interval_minutes=interval_minutes,
            cache_dir=cache_dir,
            prob_source="model",
            model_bundle_path=model_path,
        )
        summary = backtest_tsa.summarize(df)
        row["backtest_pnl_total"] = summary.get("pnl_total")
        row["backtest_pnl_avg"] = summary.get("pnl_avg")
        row["backtest_brier"] = summary.get("brier")
        row["backtest_logloss"] = summary.get("logloss")
        # hit_rate proxy = average predicted probability for chosen side relative to outcomes
        row["backtest_hit_rate_proxy"] = float((df["outcome"] == 1).mean()) if not df.empty else None
    return row


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TSA feature ablation and summarize model/backtest metrics.")
    parser.add_argument("--dataset-csv", type=Path, default=DEFAULT_DATASET, help="Contract dataset CSV")
    parser.add_argument("--feature-sets-json", type=str, default=None, help="Optional JSON file mapping set name -> feature list")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Output report directory")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR, help="Output ablation model directory")
    parser.add_argument("--start", required=True, help="Backtest start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Backtest end date YYYY-MM-DD")
    parser.add_argument("--interval", type=int, default=1440, help="Backtest candle interval in minutes")
    parser.add_argument(
        "--cache",
        type=Path,
        default=backtest_tsa.DEFAULT_CACHE,
        help="Backtest candle cache directory",
    )
    parser.add_argument("--train-weeks", type=int, default=12, help="Walk-forward train weeks")
    parser.add_argument("--val-weeks", type=int, default=4, help="Walk-forward validation weeks")
    parser.add_argument("--step-weeks", type=int, default=2, help="Walk-forward step weeks")
    parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="Train ablations only; skip model backtests",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    feature_sets = _parse_feature_sets(args.feature_sets_json)
    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    args.model_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []
    for name, features in feature_sets.items():
        print(f"[ablation] running: {name} ({len(features)} features)")
        row = _run_single_variant(
            name=name,
            features=features,
            dataset_csv=args.dataset_csv,
            model_dir=args.model_dir,
            train_weeks=args.train_weeks,
            val_weeks=args.val_weeks,
            step_weeks=args.step_weeks,
            run_backtest=not args.skip_backtest,
            start_date=start_date,
            end_date=end_date,
            interval_minutes=args.interval,
            cache_dir=args.cache,
        )
        rows.append(row)

    out_df = pd.DataFrame(rows)
    out_df = out_df.sort_values(by=["backtest_pnl_total", "oos_brier"], ascending=[False, True], na_position="last")

    csv_path = args.report_dir / f"tsa_feature_ablation_{run_ts}.csv"
    md_path = args.report_dir / f"tsa_feature_ablation_{run_ts}.md"
    out_df.to_csv(csv_path, index=False)
    md_path.write_text(
        _render_markdown(
            rows=out_df,
            run_ts=run_ts,
            dataset_csv=args.dataset_csv,
            start_date=start_date,
            end_date=end_date,
            train_weeks=args.train_weeks,
            val_weeks=args.val_weeks,
            step_weeks=args.step_weeks,
            did_backtest=not args.skip_backtest,
        )
    )

    print(f"[ablation] csv: {csv_path}")
    print(f"[ablation] md: {md_path}")


if __name__ == "__main__":
    main()
