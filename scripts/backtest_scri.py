#!/usr/bin/env python3
"""Replay supplier snapshots against disruption labels — digital twin lite."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)

SNAPSHOT_PATTERN = re.compile(r"^supplier_snapshot_(\d{8})\.csv$")
DEFAULT_LABELS = Path("data/disruption_labels.csv")
DEFAULT_OUTPUT = Path("data/backtest/latest.json")
RISK_THRESHOLD = float(os.getenv("BACKTEST_RISK_THRESHOLD", "0.55"))
TOP_K = int(os.getenv("BACKTEST_TOP_K", "10"))


def snapshot_dir() -> Path:
    return Path(os.getenv("SNAPSHOT_DIR", "data/snapshots"))


def load_labels(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def load_snapshot_index() -> Dict[str, Dict[str, float]]:
    """Map YYYYMMDD → {supplier_id: risk_score}."""
    index: Dict[str, Dict[str, float]] = {}
    for path in sorted(snapshot_dir().glob("supplier_snapshot_*.csv")):
        match = SNAPSHOT_PATTERN.match(path.name)
        if not match:
            continue
        stamp = match.group(1)
        scores: Dict[str, float] = {}
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                sid = row.get("supplier_id")
                if not sid:
                    continue
                try:
                    scores[sid] = float(row.get("risk_score") or 0.5)
                except (TypeError, ValueError):
                    scores[sid] = 0.5
        index[stamp] = scores
    return index


def nearest_snapshot_date(event_date: str, available: List[str]) -> Optional[str]:
    """Pick closest snapshot date on or before event_date (YYYYMMDD)."""
    event_compact = event_date.replace("-", "")
    candidates = [d for d in available if d <= event_compact]
    if candidates:
        return max(candidates)
    return min(available) if available else None


def run_backtest(
    labels: List[Dict[str, Any]],
    snapshot_index: Dict[str, Dict[str, float]],
    *,
    risk_threshold: float = RISK_THRESHOLD,
    top_k: int = TOP_K,
) -> Dict[str, Any]:
    """Compute precision@K, recall, and lead-time metrics."""
    available_dates = sorted(snapshot_index.keys())
    if not available_dates:
        return {
            "status": "no_snapshots",
            "precision_at_k": None,
            "recall": None,
            "lead_time_days_median": None,
            "evaluated_labels": 0,
        }

    positives = [lb for lb in labels if str(lb.get("disrupted_30d", "")).strip() in ("1", "true", "True")]
    negative_ids = {
        lb["supplier_id"]
        for lb in labels
        if str(lb.get("disrupted_30d", "")).strip() in ("0", "false", "False")
    }

    tp = fp = fn = 0
    lead_times: List[int] = []

    for label in labels:
        sid = label.get("supplier_id")
        event_date = label.get("event_date", "")
        disrupted = str(label.get("disrupted_30d", "")).strip() in ("1", "true", "True")
        snap_date = nearest_snapshot_date(event_date, available_dates)
        if not sid or not snap_date:
            continue
        score = snapshot_index.get(snap_date, {}).get(sid)
        if score is None:
            fn += 1 if disrupted else 0
            continue

        predicted_positive = score >= risk_threshold
        if disrupted and predicted_positive:
            tp += 1
            try:
                ed = datetime.strptime(event_date, "%Y-%m-%d")
                sd = datetime.strptime(snap_date, "%Y%m%d")
                lead_times.append(max(0, (ed - sd).days))
            except ValueError:
                pass
        elif disrupted and not predicted_positive:
            fn += 1
        elif not disrupted and predicted_positive:
            fp += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    ranked: List[Tuple[str, float, bool]] = []
    for label in positives:
        sid = label.get("supplier_id")
        event_date = label.get("event_date", "")
        snap_date = nearest_snapshot_date(event_date, available_dates)
        if not sid or not snap_date:
            continue
        score = snapshot_index.get(snap_date, {}).get(sid)
        if score is not None:
            ranked.append((sid, score, True))

    for sid in list(negative_ids)[:50]:
        snap_date = available_dates[-1]
        score = snapshot_index.get(snap_date, {}).get(sid, 0.3)
        ranked.append((sid, score, False))

    ranked.sort(key=lambda x: x[1], reverse=True)
    top = ranked[:top_k]
    precision_at_k = sum(1 for _, _, pos in top if pos) / len(top) if top else 0.0

    return {
        "status": "ok",
        "precision_at_k": round(precision_at_k, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "lead_time_days_median": int(sorted(lead_times)[len(lead_times) // 2]) if lead_times else None,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "evaluated_labels": len(labels),
        "positive_labels": len(positives),
        "risk_threshold": risk_threshold,
        "top_k": top_k,
        "snapshot_dates": len(available_dates),
    }


def main() -> int:
    load_dotenv()
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )

    labels_path = Path(os.getenv("DISRUPTION_LABELS_CSV", str(DEFAULT_LABELS)))
    output_path = Path(os.getenv("BACKTEST_OUTPUT", str(DEFAULT_OUTPUT)))

    if not labels_path.is_file():
        logger.error("labels_missing", path=str(labels_path))
        return 1

    labels = load_labels(labels_path)
    snapshot_index = load_snapshot_index()
    metrics = run_backtest(labels, snapshot_index)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "labels_file": str(labels_path),
        "snapshot_dir": str(snapshot_dir()),
        **metrics,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info("backtest_complete", **metrics)
    print(json.dumps(payload, indent=2))
    return 0 if metrics.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
