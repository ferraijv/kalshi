"""Repo organization and transparency audit checks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Finding:
    level: str  # ERROR or WARN
    code: str
    message: str
    path: str | None = None


def _exists(path: Path) -> bool:
    return path.exists()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def audit_repo(root: Path = ROOT) -> List[Finding]:
    findings: List[Finding] = []

    required_docs = [
        root / "README.md",
        root / "ROADMAP.md",
        root / "AGENTS.md",
        root / "MODEL_REGISTRY.md",
        root / "reference" / "model_promotion_checklist.md",
    ]
    for path in required_docs:
        if not _exists(path):
            findings.append(Finding("ERROR", "missing_doc", "Required documentation file is missing.", str(path)))

    model_path = root / "src" / "data" / "models" / "tsa_yes_probability_model.joblib"
    schema_path = model_path.with_suffix(".schema.json")
    metadata_path = model_path.with_suffix(".metadata.json")
    for path in (model_path, schema_path, metadata_path):
        if not _exists(path):
            findings.append(Finding("ERROR", "missing_model_artifact", "Production model artifact is missing.", str(path)))

    if _exists(schema_path) and _exists(metadata_path):
        schema = _load_json(schema_path)
        metadata = _load_json(metadata_path)
        schema_features = list(schema.get("feature_names", []))
        metadata_features = list(metadata.get("feature_columns", []))
        if schema_features != metadata_features:
            findings.append(
                Finding(
                    "ERROR",
                    "schema_metadata_mismatch",
                    "schema.feature_names does not match metadata.feature_columns.",
                    str(schema_path),
                )
            )

    comparisons_dir = root / "src" / "reports" / "experiments" / "tsa_model_compare"
    comparison_reports = sorted(comparisons_dir.glob("comparison*.md")) if comparisons_dir.exists() else []
    if not comparison_reports:
        findings.append(
            Finding(
                "WARN",
                "missing_comparison_report",
                "No model comparison report found under reports/experiments/tsa_model_compare.",
                str(comparisons_dir),
            )
        )

    reports_root = root / "src" / "reports"
    if reports_root.exists():
        loose = sorted(
            p
            for p in reports_root.iterdir()
            if p.is_file() and p.suffix in {".csv", ".md", ".json"} and p.name != "README.md"
        )
        for path in loose:
            findings.append(
                Finding(
                    "WARN",
                    "loose_root_report",
                    "Report file found at src/reports root; prefer baselines/experiments/archive subfolders.",
                    str(path),
                )
            )

    return findings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit repo organization and transparency conventions.")
    parser.add_argument("--json", action="store_true", help="Print findings as JSON.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    findings = audit_repo(ROOT)
    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        if not findings:
            print("repo_audit: OK (no findings)")
        for item in findings:
            location = f" [{item.path}]" if item.path else ""
            print(f"{item.level} {item.code}: {item.message}{location}")

    has_error = any(item.level == "ERROR" for item in findings)
    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
