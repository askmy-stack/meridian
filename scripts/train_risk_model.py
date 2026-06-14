#!/usr/bin/env python3
"""Train Meridian XGBoost risk scorer with MLflow tracking."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import mlflow
import mlflow.xgboost
import numpy as np
import structlog
import xgboost as xgb
from dotenv import load_dotenv
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence.disruption_labels import (
    load_disruption_labels,
    resolve_labels_path,
    slugify_supplier_name,
    write_training_metadata,
)
from src.intelligence.feature_builder import build_supplier_features
from src.intelligence.risk_scorer import XGBoostRiskScorer

logger = structlog.get_logger(__name__)

DEFAULT_CSV = Path(__file__).parent.parent / "data" / "sample_suppliers.csv"
MODEL_DIR = Path(__file__).parent.parent / "models"
REGISTERED_NAME = "meridian-risk-scorer"


def load_training_data(
    csv_path: Path,
    *,
    labels: Dict[str, int] | None = None,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Load supplier rows, build features, and attach binary disruption labels."""
    from src.graph import get_neo4j_client

    client = None
    try:
        client = get_neo4j_client()
        client.execute_query("RETURN 1")
    except Exception:
        client = None
        logger.warning("neo4j_unavailable_for_training", message="Using CSV-only features")

    rows: List[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    label_map = labels if labels is not None else {}
    using_labels_file = bool(label_map)

    X_list: List[np.ndarray] = []
    y_list: List[int] = []
    ids: List[str] = []

    for row in rows:
        supplier_id = slugify_supplier_name(row["name"])
        risk_score = float(row.get("risk_score") or 0.5)
        critical = str(row.get("critical", "")).lower() in ("true", "1", "yes")

        if supplier_id in label_map:
            label = label_map[supplier_id]
        else:
            label = 1 if risk_score >= 0.65 or critical else 0

        features = build_supplier_features(
            supplier_id,
            single_source_flag=critical,
            critical_flag=critical,
            country_iso=row.get("country_iso"),
            neo4j_client=client,
        )
        if client is None:
            features.conflict_proximity_score = min(risk_score + 0.1, 1.0)

        X_list.append(features.to_array())
        y_list.append(label)
        ids.append(supplier_id)

    logger.info(
        "training_data_built",
        samples=len(ids),
        labels_from_file=using_labels_file,
        positive=sum(y_list),
    )
    return np.vstack(X_list), np.array(y_list), ids


def main() -> int:
    load_dotenv()
    csv_path = Path(os.getenv("TRAINING_CSV", str(DEFAULT_CSV)))
    labels_path = resolve_labels_path()
    label_map = load_disruption_labels(labels_path)
    labels_used = bool(label_map)

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", f"file:{MODEL_DIR.parent / 'mlruns'}")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "meridian-risk-scoring"))

    X, y, supplier_ids = load_training_data(csv_path, labels=label_map)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if len(set(y)) > 1 else None
    )

    params = {
        "n_estimators": int(os.getenv("XGB_N_ESTIMATORS", "120")),
        "max_depth": int(os.getenv("XGB_MAX_DEPTH", "5")),
        "learning_rate": float(os.getenv("XGB_LEARNING_RATE", "0.08")),
        "objective": "binary:logistic",
        "eval_metric": "logloss",
    }

    with mlflow.start_run(run_name="meridian-xgb-supplier-risk"):
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)

        prob = model.predict_proba(X_test)[:, 1]
        preds = (prob >= 0.5).astype(int)
        metrics = {
            "train_samples": float(len(y_train)),
            "test_samples": float(len(y_test)),
            "f1": float(f1_score(y_test, preds, zero_division=0)),
        }
        if len(set(y_test)) > 1:
            metrics["roc_auc"] = float(roc_auc_score(y_test, prob))

        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.log_param("feature_count", len(XGBoostRiskScorer.FEATURE_NAMES))
        mlflow.log_param("training_csv", str(csv_path))
        mlflow.log_param("labels_file", str(labels_path))
        mlflow.log_param("labels_used", labels_used)

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        artifact_path = MODEL_DIR / "risk_scorer.xgb"
        model.save_model(str(artifact_path))
        mlflow.log_artifact(str(artifact_path), artifact_path="model")

        write_training_metadata(
            {
                "labels_used": labels_used,
                "labels_file": str(labels_path),
                "training_csv": str(csv_path),
                "train_samples": len(y_train),
                "positive_labels": int(sum(y_train)),
                "artifact_path": str(artifact_path),
            }
        )

        mlflow.xgboost.log_model(
            model,
            artifact_path="xgb_model",
            registered_model_name=REGISTERED_NAME,
            input_example=X_train[:1],
        )

        print(f"MLflow run complete — metrics: {metrics}")
        print(f"Model saved to {artifact_path}")
        print(f"Labels file used: {labels_used} ({labels_path})")
        print(f"Tracking URI: {tracking_uri}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
