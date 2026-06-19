"""Unit tests for Phase B — RAG, conformal, event classifier, copilot stub."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.intelligence.changepoint import cusum_detect, detect_supplier_changepoint
from src.intelligence.conformal import compute_score_interval, get_calibration_quantile
from src.intelligence.event_classifier import RuleBasedEventClassifier, classify_news_event
from src.rag.embedder import Embedder

client = TestClient(app)


@pytest.fixture(autouse=True)
def _hash_embed_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_EMBED_MODE", "hash")
    monkeypatch.setenv("LLM_PROVIDER", "stub")


def test_hash_embedder_deterministic() -> None:
    emb = Embedder(force_hash=True)
    v1 = emb.embed("Red Sea shipping disruption")
    v2 = emb.embed("Red Sea shipping disruption")
    v3 = emb.embed("Taiwan semiconductor fab")
    assert len(v1) == 384
    assert v1 == v2
    assert v1 != v3
    assert emb.mode == "hash"


def test_event_classifier_armed_conflict() -> None:
    clf = RuleBasedEventClassifier()
    result = clf.classify("Missile strike near Bab el-Mandeb in Red Sea port")
    assert result.event_type == "armed_conflict"
    assert result.severity_proxy >= 0.8
    assert result.classifier == "rule-based"
    assert "risk_score" not in result.to_dict()


def test_event_classifier_sanctions() -> None:
    result = classify_news_event("New export embargo and sanctions on semiconductor trade")
    assert result.event_type == "sanctions"
    assert 0.0 <= result.severity_proxy <= 1.0


def test_conformal_interval_from_labels() -> None:
    cal = get_calibration_quantile()
    assert cal is not None
    q_hat, n_cal = cal
    assert n_cal >= 5
    interval = compute_score_interval(0.72)
    assert interval is not None
    assert interval.lower <= 0.72 <= interval.upper
    assert interval.method == "split_conformal"
    assert interval.coverage == pytest.approx(0.9)


def test_cusum_detects_spike() -> None:
    stable = [1, 1, 1, 1, 1, 1, 1]
    stat_stable, detected_stable = cusum_detect(stable, threshold=3.0)
    spiking = [1, 1, 1, 1, 8, 10, 12]
    stat_spike, detected_spike = cusum_detect(spiking, threshold=3.0)
    assert not detected_stable or stat_stable < stat_spike
    assert detected_spike


def test_changepoint_signal_structure() -> None:
    signal = detect_supplier_changepoint("sup-1", [0, 0, 1, 0, 5, 8, 10])
    payload = signal.to_dict()
    assert payload["entity_id"] == "sup-1"
    assert payload["signal_type"] == "changepoint"
    assert "cusum_statistic" in payload


def _mock_neo4j_for_copilot(query: str, params: object = None) -> list:
    """Flexible Neo4j mock for question-aware graph context."""
    if "count(s) AS suppliers" in query or (
        "OPTIONAL MATCH (s:Supplier)" in query and "affected" in query
    ):
        return [{"suppliers": 10, "events": 4, "affected": 3}]
    if "risk_score >= 0.7" in query:
        return [{"name": "Fab A", "risk": 0.9}]
    return []


def _mock_neo4j_empty_risk(query: str, params: object = None) -> list:
    if "count(s) AS suppliers" in query or (
        "OPTIONAL MATCH (s:Supplier)" in query and "affected" in query
    ):
        return [{"suppliers": 0, "events": 0, "affected": 0}]
    return []


def test_copilot_stub_red_sea() -> None:
    with patch("src.rag.copilot_service.get_neo4j_client") as mock_get, patch(
        "src.rag.copilot_service.search_routed", return_value=[]
    ):
        mock_get.return_value.execute_query.side_effect = _mock_neo4j_for_copilot
        response = client.post(
            "/intelligence/copilot",
            json={"question": "What if Red Sea shipping is attacked?"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["suggested_scenario_id"] == "red-sea-bab-el-mandeb"
    assert body["grounded"] is True
    assert body["disclaimer"]
    assert "citations" in body


def test_copilot_refuses_uncalibrated_risk_score() -> None:
    with patch("src.rag.copilot_service.get_neo4j_client") as mock_get, patch(
        "src.rag.copilot_service.search_routed", return_value=[]
    ):
        mock_get.return_value.execute_query.side_effect = _mock_neo4j_empty_risk
        response = client.post(
            "/intelligence/copilot",
            json={"question": "What is the risk score for our suppliers?"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "cannot" in body["answer"].lower() or "don't know" in body["answer"].lower()


def test_qdrant_graceful_skip_when_down() -> None:
    from src.rag.qdrant_client import QdrantStore

    store = QdrantStore(url="http://127.0.0.1:1")
    assert store.is_available is False
    assert store.search("meridian_events", [0.0] * 384, limit=3) == []


def test_weak_signals_endpoint_mocked() -> None:
    with patch("src.api.routes.intelligence_extended.get_neo4j_client") as mock_get, patch(
        "src.intelligence.changepoint.fetch_supplier_event_counts",
        return_value=[0, 0, 1, 0, 6, 8, 9],
    ), patch(
        "src.intelligence.weak_signal_detector.get_weak_signal_detector"
    ) as mock_detector:
        mock_get.return_value = MagicMock()
        mock_detector.return_value.monitor_supplier.return_value = ([], None)
        response = client.get("/intelligence/suppliers/sup-1/weak-signals")
    assert response.status_code == 200
    body = response.json()
    assert body["supplier_id"] == "sup-1"
    assert "changepoint" in body
    assert "signals" in body
