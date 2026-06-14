"""Regional stress regime detection via 3-state HMM (stable / escalation / crisis)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

REGIME_LABELS = ("stable", "escalation", "crisis")

try:
    from hmmlearn.hmm import GaussianHMM

    HMMLEARN_AVAILABLE = True
except ImportError:
    HMMLEARN_AVAILABLE = False
    GaussianHMM = None  # type: ignore


@dataclass
class RegimeAssessment:
    """Current regional stress regime and transition context."""

    region_id: str
    regime: str
    confidence: float
    event_rate: float
    method: str
    transition_probs: Dict[str, float]
    history_days: int
    disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "regime": self.regime,
            "confidence": round(self.confidence, 4),
            "event_rate": round(self.event_rate, 4),
            "method": self.method,
            "transition_probs": {k: round(v, 4) for k, v in self.transition_probs.items()},
            "history_days": self.history_days,
            "disclaimer": self.disclaimer,
        }


def _threshold_regime(event_rate: float) -> Tuple[str, float]:
    """Simple fallback when hmmlearn is unavailable."""
    if event_rate >= 0.75:
        return "crisis", min(0.95, 0.6 + event_rate * 0.3)
    if event_rate >= 0.45:
        return "escalation", min(0.9, 0.5 + event_rate * 0.35)
    return "stable", min(0.9, 0.55 + (1.0 - event_rate) * 0.3)


def _fit_hmm_regime(series: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
    """Fit 3-state Gaussian HMM on daily event-rate observations."""
    if not HMMLEARN_AVAILABLE or len(series) < 5:
        rate = float(np.mean(series[-7:])) if len(series) else 0.0
        regime, conf = _threshold_regime(rate)
        return regime, conf, {label: 1.0 / 3 for label in REGIME_LABELS}

    x = series.reshape(-1, 1)
    model = GaussianHMM(n_components=3, covariance_type="diag", n_iter=50, random_state=42)
    try:
        model.fit(x)
        states = model.predict(x)
        means = model.means_.flatten()
        order = np.argsort(means)
        label_map = {order[i]: REGIME_LABELS[i] for i in range(3)}
        current_state = int(states[-1])
        regime = label_map[current_state]
        posteriors = model.predict_proba(x)[-1]
        confidence = float(posteriors[current_state])
        trans = model.transmat_[current_state]
        transition_probs = {
            label_map[i]: float(trans[i]) for i in range(3)
        }
        return regime, confidence, transition_probs
    except Exception as exc:
        logger.warning("hmm_fit_failed", error=str(exc))
        rate = float(np.mean(series[-7:]))
        regime, conf = _threshold_regime(rate)
        return regime, conf, {label: 1.0 / 3 for label in REGIME_LABELS}


def assess_regime_from_series(
    region_id: str,
    daily_rates: Sequence[float],
) -> RegimeAssessment:
    """Classify regime from a daily event-rate time series."""
    series = np.asarray(daily_rates, dtype=float)
    if len(series) == 0:
        return RegimeAssessment(
            region_id=region_id,
            regime="stable",
            confidence=0.0,
            event_rate=0.0,
            method="insufficient_data",
            transition_probs={label: 0.0 for label in REGIME_LABELS},
            history_days=0,
            disclaimer="No event-rate observations for this region.",
        )

    regime, confidence, transition_probs = _fit_hmm_regime(series)
    method = "hmmlearn" if HMMLEARN_AVAILABLE and len(series) >= 5 else "threshold_fallback"
    current_rate = float(series[-1])

    return RegimeAssessment(
        region_id=region_id,
        regime=regime,
        confidence=confidence,
        event_rate=current_rate,
        method=method,
        transition_probs=transition_probs,
        history_days=len(series),
        disclaimer=(
            "Regional stress regime from event-rate time series — not a SCRI score. "
            "HMM states: stable / escalation / crisis."
        ),
    )


def _zone_countries(region_id: str) -> List[str]:
    """Map conflict zone id to ISO country codes."""
    from ..geopolitical.conflict_zones import CONFLICT_ZONES

    for zone in CONFLICT_ZONES:
        if zone["id"] == region_id:
            return list(zone.get("countries") or [])
    return []


def _synthetic_rates_from_zone(region_id: str, days: int) -> List[float]:
    """Build demo event-rate series from static zone severity when Neo4j is empty."""
    from ..geopolitical.conflict_zones import CONFLICT_ZONES

    base = 0.35
    for zone in CONFLICT_ZONES:
        if zone["id"] == region_id:
            base = float(zone.get("severity", 0.5)) * 0.85
            break
    rng = np.random.default_rng(abs(hash(region_id)) % (2**32))
    noise = rng.normal(0, 0.06, size=days)
    trend = np.linspace(base * 0.9, base, days)
    rates = np.clip(trend + noise, 0.05, 1.0)
    return rates.tolist()


def fetch_regional_event_rates(region_id: str, days: int = 30) -> List[float]:
    """Daily normalized event rates for a conflict zone (Neo4j or synthetic fallback)."""
    countries = _zone_countries(region_id)
    if not countries:
        return _synthetic_rates_from_zone(region_id, days)

    try:
        from ..graph import get_neo4j_client

        client = get_neo4j_client()
        rows = client.execute_query(
            """
            MATCH (e:Event)
            WHERE e.resolved_at > datetime() - duration($window)
            OPTIONAL MATCH (e)-[:AFFECTS]->(s:Supplier)
            WITH date(e.resolved_at) AS day,
                 e,
                 coalesce(s.country_iso, e.country_iso) AS country
            WHERE country IN $countries
            RETURN day AS day, count(e) AS cnt, avg(e.severity) AS avg_sev
            ORDER BY day
            """,
            {"window": f"P{days}D", "countries": countries},
        )
        if not rows:
            return _synthetic_rates_from_zone(region_id, days)

        counts = [float(r.get("cnt") or 0) for r in rows]
        severities = [float(r.get("avg_sev") or 0.5) for r in rows]
        max_cnt = max(counts) if counts else 1.0
        rates = [
            min(1.0, 0.5 * (c / max_cnt) + 0.5 * s)
            for c, s in zip(counts, severities, strict=True)
        ]
        while len(rates) < days:
            rates.insert(0, rates[0] if rates else 0.3)
        return rates[-days:]
    except Exception as exc:
        logger.warning("regional_rates_neo4j_failed", region_id=region_id, error=str(exc))
        return _synthetic_rates_from_zone(region_id, days)


def assess_region_regime(region_id: str, days: int = 30) -> RegimeAssessment:
    """End-to-end regime assessment for a conflict zone id."""
    rates = fetch_regional_event_rates(region_id, days=days)
    return assess_regime_from_series(region_id, rates)


def regime_summary_all_regions(days: int = 30) -> Dict[str, Any]:
    """Summarize regimes across all reference conflict zones."""
    from ..geopolitical.conflict_zones import CONFLICT_ZONES

    regions = []
    for zone in CONFLICT_ZONES:
        assessment = assess_region_regime(zone["id"], days=days)
        payload = assessment.to_dict()
        payload["name"] = zone["name"]
        payload["severity_baseline"] = zone.get("severity")
        regions.append(payload)

    crisis_count = sum(1 for r in regions if r["regime"] == "crisis")
    escalation_count = sum(1 for r in regions if r["regime"] == "escalation")
    return {
        "regions": regions,
        "summary": {
            "total": len(regions),
            "crisis": crisis_count,
            "escalation": escalation_count,
            "stable": len(regions) - crisis_count - escalation_count,
        },
        "history_days": days,
    }
