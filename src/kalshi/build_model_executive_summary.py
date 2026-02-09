"""Build a one-page executive summary of TSA model status and performance."""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[2]
MODEL_REGISTRY_PATH = ROOT / "MODEL_REGISTRY.md"
COMPARE_RUNS_DIR = ROOT / "src" / "reports" / "experiments" / "tsa_model_compare" / "runs"
ABLATION_DIR = ROOT / "src" / "reports" / "experiments" / "tsa_feature_ablation"
DEFAULT_OUTPUT = ROOT / "reference" / "model_executive_summary.md"


def _parse_markdown_table_rows(markdown: str) -> List[Dict[str, str]]:
    """Return table rows from the first markdown table in a document."""
    lines = markdown.splitlines()
    for idx in range(len(lines) - 2):
        header = lines[idx].strip()
        divider = lines[idx + 1].strip()
        if not (header.startswith("|") and header.endswith("|")):
            continue
        if "---" not in divider:
            continue

        headers = [cell.strip() for cell in header.strip("|").split("|")]
        rows: List[Dict[str, str]] = []
        j = idx + 2
        while j < len(lines):
            row = lines[j].strip()
            if not (row.startswith("|") and row.endswith("|")):
                break
            cells = [cell.strip() for cell in row.strip("|").split("|")]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
            j += 1
        return rows
    return []


def _parse_named_table(markdown: str, section_title: str) -> List[Dict[str, str]]:
    """Return rows from a markdown table under a section header."""
    marker = f"## {section_title}"
    if marker not in markdown:
        return []
    section = markdown.split(marker, 1)[1]
    return _parse_markdown_table_rows(section)


def _active_registry_entry(registry_path: Path) -> Optional[Dict[str, str]]:
    rows = _parse_named_table(registry_path.read_text(), "Entries")
    for row in rows:
        if row.get("status", "").strip().upper() == "ACTIVE":
            return row
    return None


def _latest_compare_run_dir(runs_dir: Path) -> Optional[Path]:
    if not runs_dir.exists():
        return None
    dirs = sorted(path for path in runs_dir.iterdir() if path.is_dir())
    if not dirs:
        return None
    return dirs[-1]


def _coerce_float(value: str) -> float:
    return float(value.replace(",", ""))


def _comparison_metrics(compare_path: Path) -> Dict[str, Dict[str, float]]:
    rows = _parse_named_table(compare_path.read_text(), "KPI Delta Table")
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        metric = row.get("metric")
        if not metric:
            continue
        out[metric] = {
            "baseline": _coerce_float(row["baseline"]),
            "candidate": _coerce_float(row["candidate"]),
            "delta_abs": _coerce_float(row["delta_abs"]),
            "delta_pct": _coerce_float(row["delta_pct"]),
        }
    return out


def _latest_ablation_report(ablation_dir: Path) -> Optional[Path]:
    if not ablation_dir.exists():
        return None
    reports = sorted(ablation_dir.glob("tsa_feature_ablation_*.md"))
    if not reports:
        return None
    return reports[-1]


def _best_ablation_variant(ablation_path: Path) -> Optional[Dict[str, str]]:
    rows = _parse_named_table(ablation_path.read_text(), "Results")
    if not rows:
        return None
    return rows[0]


def _go_no_go(metrics: Dict[str, Dict[str, float]]) -> Dict[str, str]:
    must_improve = ["pnl_total", "brier_mean", "logloss_mean", "ece"]
    checks: Dict[str, bool] = {}
    checks["pnl_total"] = metrics.get("pnl_total", {}).get("delta_abs", 0.0) > 0.0
    checks["brier_mean"] = metrics.get("brier_mean", {}).get("delta_abs", 0.0) < 0.0
    checks["logloss_mean"] = metrics.get("logloss_mean", {}).get("delta_abs", 0.0) < 0.0
    checks["ece"] = metrics.get("ece", {}).get("delta_abs", 0.0) < 0.0
    drawdown_delta = metrics.get("max_drawdown", {}).get("delta_abs", 0.0)

    core_pass = all(checks[name] for name in must_improve)
    if core_pass and drawdown_delta <= 0.0:
        status = "GO"
        reason = "Candidate improves calibration/loss/PnL and does not worsen drawdown."
    elif core_pass and drawdown_delta > 0.0:
        status = "GO WITH RISK REVIEW"
        reason = "Candidate improves core KPIs but increases drawdown; risk sign-off required."
    else:
        status = "NO-GO"
        reason = "Candidate fails one or more core promotion checks."
    return {"status": status, "reason": reason}


def render_summary(
    generated_at: str,
    active_model: Optional[Dict[str, str]],
    latest_compare_run: Optional[Path],
    compare_metrics: Dict[str, Dict[str, float]],
    best_variant: Optional[Dict[str, str]],
    ablation_path: Optional[Path],
) -> str:
    lines: List[str] = []
    lines.append("# Model Executive Summary")
    lines.append("")
    lines.append(f"- generated_at: `{generated_at}`")
    lines.append("")

    go = _go_no_go(compare_metrics) if compare_metrics else {"status": "UNKNOWN", "reason": "No comparison metrics found."}
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- status: `{go['status']}`")
    lines.append(f"- rationale: {go['reason']}")
    lines.append("")

    lines.append("## Promoted Model")
    lines.append("")
    if active_model is None:
        lines.append("- No ACTIVE model entry found in `MODEL_REGISTRY.md`.")
    else:
        lines.append(f"- model_id: `{active_model.get('model_id', '')}`")
        lines.append(f"- promoted_at: `{active_model.get('promoted_at', '')}`")
        lines.append(f"- feature_set: `{active_model.get('feature_set', '')}`")
        lines.append(f"- model_path: `{active_model.get('model_path', '')}`")
    lines.append("")

    lines.append("## Baseline vs Candidate (Latest Run)")
    lines.append("")
    if latest_compare_run is None or not compare_metrics:
        lines.append("- No comparison run found under `src/reports/experiments/tsa_model_compare/runs/`.")
    else:
        lines.append(f"- run_id: `{latest_compare_run.name}`")
        lines.append(f"- comparison_report: `{latest_compare_run / 'comparison.md'}`")
        lines.append("")
        lines.append("| metric | baseline | candidate | delta_abs |")
        lines.append("| --- | --- | --- | --- |")
        for key in ("pnl_total", "brier_mean", "logloss_mean", "ece", "max_drawdown", "sharpe_like"):
            if key not in compare_metrics:
                continue
            item = compare_metrics[key]
            lines.append(
                f"| {key} | {item['baseline']:.6f} | {item['candidate']:.6f} | {item['delta_abs']:.6f} |"
            )
    lines.append("")

    lines.append("## Best Ablation Variant (Latest Report)")
    lines.append("")
    if ablation_path is None or best_variant is None:
        lines.append("- No ablation report found.")
    else:
        lines.append(f"- report: `{ablation_path}`")
        lines.append(f"- variant: `{best_variant.get('name', '')}`")
        lines.append(f"- features: `{best_variant.get('features', '')}`")
        lines.append(f"- oos_brier: `{best_variant.get('oos_brier', '')}`")
        lines.append(f"- oos_logloss: `{best_variant.get('oos_logloss', '')}`")
        lines.append(f"- oos_auc: `{best_variant.get('oos_auc', '')}`")
        lines.append(f"- backtest_pnl_total: `{best_variant.get('backtest_pnl_total', '')}`")
    lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build executive summary for TSA model status.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output markdown path")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    active_model = _active_registry_entry(MODEL_REGISTRY_PATH) if MODEL_REGISTRY_PATH.exists() else None
    latest_compare_run = _latest_compare_run_dir(COMPARE_RUNS_DIR)
    compare_metrics: Dict[str, Dict[str, float]] = {}
    if latest_compare_run is not None:
        compare_md = latest_compare_run / "comparison.md"
        if compare_md.exists():
            compare_metrics = _comparison_metrics(compare_md)

    ablation_path = _latest_ablation_report(ABLATION_DIR)
    best_variant = _best_ablation_variant(ablation_path) if ablation_path is not None else None

    summary = render_summary(
        generated_at=generated_at,
        active_model=active_model,
        latest_compare_run=latest_compare_run,
        compare_metrics=compare_metrics,
        best_variant=best_variant,
        ablation_path=ablation_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(summary)
    print(f"Wrote executive summary: {args.output}")


if __name__ == "__main__":
    main()
