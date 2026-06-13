"""Unit tests for risk scorer and feature builder."""

from __future__ import annotations

import numpy as np

from src.intelligence.feature_builder import build_supplier_features
from src.intelligence.risk_scorer import FeatureVector, XGBoostRiskScorer


def test_feature_vector_shape() -> None:
    vec = FeatureVector(conflict_proximity_score=0.8, single_source_flag=True)
    arr = vec.to_array()
    assert arr.shape == (13,)
    assert 0.0 <= arr[0] <= 1.0


def test_build_supplier_features_without_neo4j() -> None:
    features = build_supplier_features(
        "test-supplier",
        single_source_flag=True,
        critical_flag=True,
        country_iso="TW",
        neo4j_client=None,
    )
    assert features.single_source_flag is True
    assert features.political_stability_index == 0.62


def test_xgboost_scorer_returns_shap_factors() -> None:
    scorer = XGBoostRiskScorer(use_shap=True)
    result = scorer.score(
        "demo-supplier",
        "supplier",
        FeatureVector(conflict_proximity_score=0.9, single_source_flag=True, critical_events_count=2),
    )
    assert 0.0 <= result.risk_score <= 1.0
    assert result.risk_category in {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert isinstance(result.top_factors, list)
