"""Shared contract-level probability feature building and sklearn inference."""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import joblib
import numpy as np
import pandas as pd


DEFAULT_MODEL_BUNDLE = Path(__file__).resolve().parents[1] / "data" / "models" / "tsa_yes_probability_model.joblib"
DEFAULT_SCHEMA_PATH = DEFAULT_MODEL_BUNDLE.with_suffix(".schema.json")
EPS = 1e-9


@dataclass
class SklearnBundle:
    """Persisted sklearn model and feature schema for yes-probability inference."""

    feature_names: List[str]
    schema_version: str
    model_version: str
    model: object

    @classmethod
    def from_schema_and_model(cls, schema: Dict[str, object], model: object) -> "SklearnBundle":
        """Build a bundle from schema JSON and a loaded sklearn model."""
        required = {"feature_names", "schema_version", "model_version"}
        missing = required - set(schema)
        if missing:
            raise ValueError(f"Model schema missing required keys: {sorted(missing)}")
        feature_names = list(schema["feature_names"])  # type: ignore[arg-type]
        if not feature_names:
            raise ValueError("Model schema feature_names must not be empty.")
        if not hasattr(model, "predict_proba"):
            raise ValueError("Loaded model must implement predict_proba.")

        return cls(
            feature_names=feature_names,
            schema_version=str(schema["schema_version"]),
            model_version=str(schema["model_version"]),
            model=model,
        )

    def predict_yes_probability(self, features: pd.DataFrame) -> np.ndarray:
        """Return per-row P(YES wins) for a feature DataFrame."""
        missing = [name for name in self.feature_names if name not in features.columns]
        if missing:
            raise ValueError(f"Input features missing required columns: {missing}")
        ordered = features[self.feature_names].astype(float)
        proba = self.model.predict_proba(ordered)
        if getattr(proba, "shape", None) is None or proba.shape[1] < 2:
            raise ValueError("Model predict_proba output is malformed for binary classification.")
        probs = np.asarray(proba[:, 1], dtype=float)
        return np.clip(probs, EPS, 1.0 - EPS)


def model_bundle_exists(model_bundle_path: Path = DEFAULT_MODEL_BUNDLE) -> bool:
    """Return True when a model bundle JSON is available."""
    schema_path = model_bundle_path.with_suffix(".schema.json")
    return model_bundle_path.exists() and schema_path.exists()


def load_sklearn_bundle(model_bundle_path: Path = DEFAULT_MODEL_BUNDLE) -> SklearnBundle:
    """Load sklearn model bundle from disk."""
    schema_path = model_bundle_path.with_suffix(".schema.json")
    schema = json.loads(schema_path.read_text())
    model = joblib.load(model_bundle_path)
    return SklearnBundle.from_schema_and_model(schema=schema, model=model)


def save_sklearn_bundle(
    model: object,
    feature_names: Sequence[str],
    model_bundle_path: Path = DEFAULT_MODEL_BUNDLE,
    schema_version: str = "v1",
    model_version: str = "logistic-baseline",
) -> None:
    """Persist sklearn model and schema as a bundle for inference."""
    model_bundle_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_bundle_path)
    schema = {
        "feature_names": list(feature_names),
        "schema_version": schema_version,
        "model_version": model_version,
    }
    model_bundle_path.with_suffix(".schema.json").write_text(json.dumps(schema, indent=2, sort_keys=True))


def _days_until_sunday_from_run_date(run_date: datetime.date) -> int:
    """Return calendar days between run_date and target Sunday (Sunday -> 6)."""
    days_until_sunday = (6 - run_date.weekday()) % 7
    return 6 if days_until_sunday == 0 else days_until_sunday


def build_contract_feature_row(
    prediction_passengers: float,
    floor_strike: float,
    run_date: datetime.date,
    prediction_context: Optional[Dict[str, object]] = None,
) -> Dict[str, float]:
    """Build one point-in-time contract feature row."""
    context = prediction_context or {}
    strike_distance_pct = (prediction_passengers / floor_strike) - 1.0
    return {
        # Keep raw units for readability/debugging.
        "prediction_passengers": float(prediction_passengers),
        "floor_strike": float(floor_strike),
        # Training schema currently uses strike in millions.
        "floor_strike_millions": float(floor_strike) / 1_000_000.0,
        "strike_distance_pct": float(strike_distance_pct),
        "abs_strike_distance_pct": float(abs(strike_distance_pct)),
        "days_until_sunday": float(_days_until_sunday_from_run_date(run_date)),
        "day_1_trend": float(context.get("day_1_trend", 1.0)),
        "day_7_trend": float(context.get("day_7_trend", 1.0)),
        "yoy_adjustment": float(context.get("yoy_adjustment", 1.0)),
        "last_year_passengers": float(context.get("last_year_passengers", prediction_passengers)),
    }


def build_contract_feature_frame(
    rows: Iterable[Dict[str, float]],
) -> pd.DataFrame:
    """Return a DataFrame for model inference from feature row dictionaries."""
    return pd.DataFrame(list(rows))


def map_yes_probability_to_side(prob_yes: float) -> tuple[str, float]:
    """Map P(YES) into best side and side win probability."""
    if prob_yes >= 0.5:
        return "yes", prob_yes
    return "no", 1.0 - prob_yes


def predict_yes_probability(
    prediction_passengers: float,
    floor_strike: float,
    run_date: datetime.date,
    prediction_context: Optional[Dict[str, object]] = None,
    model_bundle_path: Path = DEFAULT_MODEL_BUNDLE,
) -> Optional[float]:
    """Return model-based P(YES) when bundle exists; otherwise None."""
    if not model_bundle_exists(model_bundle_path):
        return None
    try:
        bundle = load_sklearn_bundle(model_bundle_path)
        features = build_contract_feature_frame(
            [
                build_contract_feature_row(
                    prediction_passengers=prediction_passengers,
                    floor_strike=floor_strike,
                    run_date=run_date,
                    prediction_context=prediction_context,
                )
            ]
        )
        return float(bundle.predict_yes_probability(features)[0])
    except (ValueError, TypeError):
        # If model/schema/features are incompatible at runtime, fall back to heuristic caller path.
        return None
