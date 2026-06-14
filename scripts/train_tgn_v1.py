#!/usr/bin/env python3
"""Train TGN v1 research checkpoint — lightweight GRU on supplier score sequences."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)

SNAPSHOT_PATTERN = re.compile(r"^supplier_snapshot_(\d{8})\.csv$")
SEQ_LEN = 7
MIN_SNAPSHOTS = 7
DEFAULT_MODEL_PATH = Path("models/tgn_v1.pt")


@dataclass
class TrainingSequence:
    """Input sequence and next-step label for one supplier."""

    supplier_id: str
    features: np.ndarray
    label: float


def snapshot_dir() -> Path:
    return Path(os.getenv("SNAPSHOT_DIR", "data/snapshots"))


def load_manifest() -> Dict[str, Any]:
    path = snapshot_dir() / "tgn_manifest.json"
    if not path.is_file():
        return {"ready_for_training": False, "snapshot_count": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def discover_snapshot_paths() -> List[Path]:
    directory = snapshot_dir()
    paths = []
    for path in sorted(directory.glob("supplier_snapshot_*.csv")):
        if SNAPSHOT_PATTERN.match(path.name):
            paths.append(path)
    return paths


def build_sequences(paths: List[Path], seq_len: int = SEQ_LEN) -> List[TrainingSequence]:
    """Build (seq_len → next score) training pairs from ordered snapshots."""
    by_supplier: Dict[str, List[Tuple[str, float]]] = {}
    for path in paths:
        date_stamp = SNAPSHOT_PATTERN.match(path.name).group(1)  # type: ignore[union-attr]
        with path.open(encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                sid = row.get("supplier_id")
                if not sid:
                    continue
                try:
                    score = float(row.get("risk_score") or 0.5)
                except (TypeError, ValueError):
                    score = 0.5
                by_supplier.setdefault(sid, []).append((date_stamp, score))

    sequences: List[TrainingSequence] = []
    for sid, entries in by_supplier.items():
        entries.sort(key=lambda x: x[0])
        scores = [s for _, s in entries]
        if len(scores) <= seq_len:
            continue
        for i in range(len(scores) - seq_len):
            window = np.array(scores[i : i + seq_len], dtype=np.float32).reshape(seq_len, 1)
            label = float(scores[i + seq_len])
            sequences.append(TrainingSequence(supplier_id=sid, features=window, label=label))
    return sequences


def train_gru(
    sequences: List[TrainingSequence],
    *,
    epochs: int = 30,
    hidden_size: int = 16,
) -> Tuple[Any, Dict[str, float]]:
    """Train a tiny GRU regressor; falls back to sklearn if PyTorch unavailable."""
    x = np.stack([s.features for s in sequences], axis=0)
    y = np.array([s.label for s in sequences], dtype=np.float32)

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        class TinyGRU(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.gru = nn.GRU(input_size=1, hidden_size=hidden_size, batch_first=True)
                self.head = nn.Linear(hidden_size, 1)

            def forward(self, batch: torch.Tensor) -> torch.Tensor:
                out, _ = self.gru(batch)
                return self.head(out[:, -1, :]).squeeze(-1)

        device = torch.device("cpu")
        model = TinyGRU().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        loss_fn = nn.MSELoss()

        xt = torch.tensor(x, dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.float32)
        loader = DataLoader(TensorDataset(xt, yt), batch_size=min(32, len(x)), shuffle=True)

        model.train()
        last_loss = 0.0
        for _ in range(epochs):
            for batch_x, batch_y in loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                optimizer.zero_grad()
                pred = model(batch_x)
                loss = loss_fn(pred, batch_y)
                loss.backward()
                optimizer.step()
                last_loss = float(loss.item())

        model.eval()
        with torch.no_grad():
            preds = model(xt.to(device)).cpu().numpy()
        mae = float(np.mean(np.abs(preds - y)))

        metrics = {"train_mae": round(mae, 4), "final_loss": round(last_loss, 6), "backend": "pytorch_gru"}
        return model, metrics
    except Exception as exc:
        logger.warning("pytorch_gru_failed", error=str(exc))
        from sklearn.linear_model import Ridge

        flat = x.reshape(len(x), -1)
        reg = Ridge(alpha=1.0)
        reg.fit(flat, y)
        preds = reg.predict(flat)
        mae = float(np.mean(np.abs(preds - y)))
        metrics = {"train_mae": round(mae, 4), "backend": "sklearn_ridge_fallback"}
        return reg, metrics


def save_checkpoint(model: Any, path: Path, meta: Dict[str, Any]) -> None:
    """Persist model weights and metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import torch

        if hasattr(model, "state_dict"):
            payload = {
                "model_state": model.state_dict(),
                "meta": meta,
                "seq_len": SEQ_LEN,
                "backend": "pytorch_gru",
            }
            torch.save(payload, path)
            return
    except Exception:
        pass

    import joblib

    joblib.dump({"model": model, "meta": meta, "seq_len": SEQ_LEN, "backend": "sklearn"}, path)


def log_mlflow(metrics: Dict[str, Any], *, stub: bool) -> None:
    """Log training run to MLflow (or research_stub tag when insufficient data)."""
    try:
        import mlflow

        uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment("tgn_v1_research")
        with mlflow.start_run(run_name=f"tgn_v1_{datetime.utcnow().strftime('%Y%m%d')}"):
            if stub:
                mlflow.set_tag("status", "research_stub")
            else:
                mlflow.set_tag("status", "trained")
            for key, val in metrics.items():
                if isinstance(val, (int, float)):
                    mlflow.log_metric(key, val)
    except Exception as exc:
        logger.warning("mlflow_log_failed", error=str(exc))


def main() -> int:
    load_dotenv()
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )

    manifest = load_manifest()
    paths = discover_snapshot_paths()
    model_path = Path(os.getenv("TGN_MODEL_PATH", str(DEFAULT_MODEL_PATH)))

    if len(paths) < MIN_SNAPSHOTS:
        logger.warning(
            "tgn_v1_insufficient_snapshots",
            have=len(paths),
            need=MIN_SNAPSHOTS,
        )
        log_mlflow(
            {"snapshot_count": len(paths), "ready": 0},
            stub=True,
        )
        return 1

    sequences = build_sequences(paths)
    if len(sequences) < 10:
        logger.warning("tgn_v1_insufficient_sequences", count=len(sequences))
        log_mlflow({"sequence_count": len(sequences), "ready": 0}, stub=True)
        return 1

    model, metrics = train_gru(sequences)
    meta = {
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "snapshot_count": len(paths),
        "sequence_count": len(sequences),
        "manifest_ready": manifest.get("ready_for_training", False),
        **metrics,
    }
    save_checkpoint(model, model_path, meta)
    log_mlflow(
        {
            "snapshot_count": len(paths),
            "sequence_count": len(sequences),
            "train_mae": metrics.get("train_mae", 0),
        },
        stub=False,
    )
    logger.info("tgn_v1_trained", path=str(model_path), **metrics)
    print(f"Saved TGN v1 checkpoint to {model_path} (MAE={metrics.get('train_mae')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
