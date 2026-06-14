"""Load historical disruption labels for risk model training."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LABELS_PATH = REPO_ROOT / "data" / "disruption_labels.csv"
TRAINING_METADATA_PATH = REPO_ROOT / "models" / "training_metadata.json"


def slugify_supplier_name(name: str) -> str:
    """Normalize supplier name to the slug id used in training joins."""
    return name.lower().replace(" ", "-").replace(".", "")


def resolve_labels_path(path: Optional[Path] = None) -> Path:
    """Return the configured disruption labels CSV path."""
    import os

    explicit = os.getenv("DISRUPTION_LABELS_CSV")
    if explicit:
        return Path(explicit)
    return path or DEFAULT_LABELS_PATH


def labels_file_available(path: Optional[Path] = None) -> bool:
    """True when a disruption labels CSV exists on disk."""
    return resolve_labels_path(path).is_file()


def load_disruption_labels(path: Optional[Path] = None) -> Dict[str, int]:
    """Load supplier_id → binary label (1 if any row disrupted within 30d)."""
    labels_path = resolve_labels_path(path)
    if not labels_path.is_file():
        logger.info("disruption_labels_missing", path=str(labels_path))
        return {}

    labels: Dict[str, int] = {}
    with labels_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            supplier_id = (row.get("supplier_id") or "").strip()
            if not supplier_id and row.get("supplier_name"):
                supplier_id = slugify_supplier_name(row["supplier_name"])
            if not supplier_id:
                continue
            disrupted = str(row.get("disrupted_30d", "0")).strip() in ("1", "true", "True")
            labels[supplier_id] = max(labels.get(supplier_id, 0), int(disrupted))

    logger.info("disruption_labels_loaded", path=str(labels_path), suppliers=len(labels))
    return labels


def read_training_metadata() -> Dict[str, Any]:
    """Return persisted training metadata written by train_risk_model.py."""
    if not TRAINING_METADATA_PATH.is_file():
        return {}
    try:
        return json.loads(TRAINING_METADATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("training_metadata_invalid", path=str(TRAINING_METADATA_PATH))
        return {}


def write_training_metadata(metadata: Dict[str, Any]) -> None:
    """Persist training provenance for model_status / methodology."""
    TRAINING_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRAINING_METADATA_PATH.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def used_validated_labels_for_training() -> bool:
    """True when the deployed model was trained with disruption_labels.csv."""
    meta = read_training_metadata()
    return bool(meta.get("labels_used")) and labels_file_available(
        Path(meta["labels_file"]) if meta.get("labels_file") else None
    )
