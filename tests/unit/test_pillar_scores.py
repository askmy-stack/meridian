"""Unit tests for SCRI pillar score decomposition."""

from __future__ import annotations

from src.intelligence.feature_builder import compute_pillar_scores
from src.intelligence.risk_scorer import FeatureVector


def test_compute_pillar_scores_returns_four_pillars() -> None:
    features = FeatureVector(
        conflict_proximity_score=0.8,
        political_stability_index=0.4,
        port_congestion_score=0.5,
        weather_risk_score=0.3,
        recent_events_count=4,
        critical_events_count=2,
        single_source_flag=True,
        dependency_depth=2,
    )
    scores = compute_pillar_scores(features)
    assert set(scores.keys()) == {"geographic", "operational", "network", "event_load"}
    assert all(0.0 <= value <= 1.0 for value in scores.values())
