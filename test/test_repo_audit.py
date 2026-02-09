from pathlib import Path

from src.kalshi import repo_audit


def _touch(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_repo_audit_ok_when_required_files_present(tmp_path):
    _touch(tmp_path / "README.md")
    _touch(tmp_path / "ROADMAP.md")
    _touch(tmp_path / "AGENTS.md")
    _touch(tmp_path / "MODEL_REGISTRY.md")
    _touch(tmp_path / "reference" / "model_promotion_checklist.md")
    _touch(tmp_path / "src" / "data" / "models" / "tsa_yes_probability_model.joblib", "bin")
    _touch(
        tmp_path / "src" / "data" / "models" / "tsa_yes_probability_model.schema.json",
        '{"feature_names": ["a"], "schema_version": "v1", "model_version": "m1"}',
    )
    _touch(
        tmp_path / "src" / "data" / "models" / "tsa_yes_probability_model.metadata.json",
        '{"feature_columns": ["a"]}',
    )
    _touch(
        tmp_path / "src" / "reports" / "experiments" / "tsa_model_compare" / "comparison_x.md",
        "# report",
    )
    _touch(tmp_path / "src" / "reports" / "INDEX.md", "# index")

    findings = repo_audit.audit_repo(tmp_path)
    assert findings == []


def test_repo_audit_flags_schema_metadata_mismatch(tmp_path):
    _touch(tmp_path / "README.md")
    _touch(tmp_path / "ROADMAP.md")
    _touch(tmp_path / "AGENTS.md")
    _touch(tmp_path / "MODEL_REGISTRY.md")
    _touch(tmp_path / "reference" / "model_promotion_checklist.md")
    _touch(tmp_path / "src" / "data" / "models" / "tsa_yes_probability_model.joblib", "bin")
    _touch(
        tmp_path / "src" / "data" / "models" / "tsa_yes_probability_model.schema.json",
        '{"feature_names": ["a"], "schema_version": "v1", "model_version": "m1"}',
    )
    _touch(
        tmp_path / "src" / "data" / "models" / "tsa_yes_probability_model.metadata.json",
        '{"feature_columns": ["b"]}',
    )

    findings = repo_audit.audit_repo(tmp_path)
    codes = {item.code for item in findings}
    assert "schema_metadata_mismatch" in codes
