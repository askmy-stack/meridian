"""Lightweight changepoint detection — CUSUM on event rate per supplier."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ChangepointSignal:
    """CUSUM changepoint on event-rate time series."""

    supplier_id: str
    changepoint_detected: bool
    cusum_statistic: float
    threshold: float
    baseline_rate: float
    current_rate: float
    lookback_days: int
    description: str
    detection_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": "changepoint",
            "entity_id": self.supplier_id,
            "entity_type": "supplier",
            "changepoint_detected": self.changepoint_detected,
            "cusum_statistic": round(self.cusum_statistic, 4),
            "threshold": round(self.threshold, 4),
            "baseline_rate": round(self.baseline_rate, 4),
            "current_rate": round(self.current_rate, 4),
            "lookback_days": self.lookback_days,
            "description": self.description,
            "detection_timestamp": self.detection_timestamp,
        }


def cusum_detect(
    counts: List[int],
    threshold: float = 5.0,
    drift: float = 0.5,
) -> tuple[float, bool]:
    """One-sided CUSUM on positive deviations from mean."""
    if len(counts) < 3:
        return 0.0, False

    mean = sum(counts[:-1]) / max(len(counts) - 1, 1)
    s_pos = 0.0
    for x in counts:
        s_pos = max(0.0, s_pos + (x - mean - drift))
    return s_pos, s_pos >= threshold


def detect_supplier_changepoint(
    supplier_id: str,
    daily_event_counts: List[int],
    lookback_days: int = 14,
    threshold: float = 5.0,
) -> ChangepointSignal:
    """Run CUSUM on recent vs baseline event rate."""
    window = daily_event_counts[-lookback_days:] if daily_event_counts else []
    if len(window) < 3:
        return ChangepointSignal(
            supplier_id=supplier_id,
            changepoint_detected=False,
            cusum_statistic=0.0,
            threshold=threshold,
            baseline_rate=0.0,
            current_rate=0.0,
            lookback_days=lookback_days,
            description="Insufficient event history for changepoint detection",
        )

    baseline = window[:-3] if len(window) > 3 else window[:1]
    recent = window[-3:]
    baseline_rate = sum(baseline) / max(len(baseline), 1)
    current_rate = sum(recent) / max(len(recent), 1)

    stat, detected = cusum_detect(window, threshold=threshold)

    if detected:
        desc = (
            f"CUSUM changepoint: event rate rose from {baseline_rate:.1f}/day "
            f"to {current_rate:.1f}/day (stat={stat:.1f})"
        )
    else:
        desc = f"Event rate stable at ~{current_rate:.1f}/day (CUSUM={stat:.1f})"

    return ChangepointSignal(
        supplier_id=supplier_id,
        changepoint_detected=detected,
        cusum_statistic=stat,
        threshold=threshold,
        baseline_rate=baseline_rate,
        current_rate=current_rate,
        lookback_days=lookback_days,
        description=desc,
    )


def fetch_supplier_event_counts(neo4j_client: Any, supplier_id: str, days: int = 14) -> List[int]:
    """Query daily event counts linked to a supplier for the last N days."""
    rows = neo4j_client.execute_query(
        """
        MATCH (e:Event)-[:AFFECTS]->(s:Supplier {id: $supplier_id})
        WHERE e.resolved_at > datetime() - duration({days: $days})
        RETURN date(e.resolved_at) AS day, count(e) AS cnt
        ORDER BY day
        """,
        {"supplier_id": supplier_id, "days": days},
    )
    if not rows:
        return [0] * days

    # Fill missing days with zeros
    today = datetime.now().date()
    day_map = {}
    for row in rows:
        day_val = row.get("day")
        if hasattr(day_val, "to_native"):
            day_val = day_val.to_native()
        if isinstance(day_val, datetime):
            day_val = day_val.date()
        day_map[str(day_val)] = int(row.get("cnt", 0))

    counts: List[int] = []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        counts.append(day_map.get(str(d), 0))
    return counts


def get_supplier_weak_signals(neo4j_client: Any, supplier_id: str) -> Dict[str, Any]:
    """Combine CUSUM changepoint with existing weak-signal detector when available."""
    counts = fetch_supplier_event_counts(neo4j_client, supplier_id)
    changepoint = detect_supplier_changepoint(supplier_id, counts)

    signals: List[Dict[str, Any]] = []
    if changepoint.changepoint_detected:
        signals.append(changepoint.to_dict())

    # Optional Isolation Forest pass
    try:
        from .weak_signal_detector import get_weak_signal_detector

        detector = get_weak_signal_detector()
        weak, forecast = detector.monitor_supplier(supplier_id, counts, counts)
        signals.extend(s.to_dict() for s in weak)
        forecast_dict = forecast.to_dict() if forecast else None
    except Exception as exc:
        logger.info("weak_signal_detector_skipped", error=str(exc))
        forecast_dict = None

    return {
        "supplier_id": supplier_id,
        "signals": signals,
        "changepoint": changepoint.to_dict(),
        "forecast": forecast_dict,
        "generated_at": datetime.now().isoformat(),
    }
