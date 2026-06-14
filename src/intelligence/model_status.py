"""Risk model deployment status — transparency for API and UI banners."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import structlog

from .disruption_labels import used_validated_labels_for_training

logger = structlog.get_logger(__name__)

ModelSource = Literal["mlflow", "file", "synthetic_default"]
TrainingStatus = Literal["validated", "demo", "untrained"]
CalibrationStatus = Literal["demo", "validated"]

_synthetic_warning_logged = False


def _default_model_path() -> Path:
    return Path(__file__).resolve().parents[2] / "models" / "risk_scorer.xgb"


def resolve_model_path() -> Optional[str]:
    """Return configured or default on-disk model path if it exists."""
    explicit = os.getenv("RISK_MODEL_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    default = _default_model_path()
    if default.exists():
        return str(default)
    return None


def detect_model_source() -> ModelSource:
    """Determine how the risk scorer was (or will be) loaded."""
    if os.getenv("MLFLOW_MODEL_URI"):
        return "mlflow"
    if resolve_model_path():
        return "file"
    return "synthetic_default"


def get_risk_model_status(*, ensure_scorer: bool = False) -> Dict[str, Any]:
    """Return model load metadata for /health and /metrics/model-status."""
    global _synthetic_warning_logged

    model_path = resolve_model_path()
    mlflow_uri = os.getenv("MLFLOW_MODEL_URI")
    source = detect_model_source()
    model_loaded = False

    if ensure_scorer:
        try:
            from .risk_scorer import get_risk_scorer

            scorer = get_risk_scorer()
            model_loaded = scorer._model is not None  # noqa: SLF001
            source = getattr(scorer, "model_source", source)
            if scorer.model_path:
                model_path = scorer.model_path
        except Exception as exc:
            logger.warning("model_status_scorer_probe_failed", error=str(exc))
    else:
        model_loaded = source in ("file", "mlflow")

    if source == "synthetic_default" and not _synthetic_warning_logged:
        logger.warning(
            "risk_model_synthetic_default",
            message=(
                "No trained risk model on disk — using in-memory XGBoost fit on "
                "synthetic labels. SCRI scores are demo-calibrated only."
            ),
        )
        _synthetic_warning_logged = True

    training_status: TrainingStatus = "validated" if source in ("file", "mlflow") else "demo"
    labels_validated = used_validated_labels_for_training()
    calibration_status: CalibrationStatus = (
        "validated"
        if training_status == "validated" and labels_validated
        else "demo"
    )

    return {
        "model_loaded": model_loaded,
        "model_path": model_path,
        "model_source": source,
        "mlflow_model_uri": mlflow_uri,
        "training_status": training_status,
        "calibration_status": calibration_status,
        "labels_validated": labels_validated,
        "is_demo_calibration": calibration_status == "demo",
    }
