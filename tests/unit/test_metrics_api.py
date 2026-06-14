"""Unit tests for metrics methodology and model status API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_metrics_methodology_returns_scri() -> None:
    response = client.get("/metrics/methodology")
    assert response.status_code == 200
    body = response.json()
    assert body["index_name"] == "SCRI"
    assert len(body["references"]) >= 2
    assert any(k["id"] == "peak_scri" for k in body["kpis"])
    assert body["calibration_status"] in ("demo", "validated")
    assert isinstance(body["limitations"], list)
    assert len(body["limitations"]) >= 2
    assert body["display_guidance"]["prefer_bands"] is True


def test_model_status_endpoint() -> None:
    response = client.get("/metrics/model-status")
    assert response.status_code == 200
    body = response.json()
    assert "model_source" in body
    assert body["model_source"] in ("mlflow", "file", "synthetic_default")
    assert body["training_status"] in ("validated", "demo", "untrained")
    assert isinstance(body["model_loaded"], bool)


def test_health_includes_model_block() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "model" in body
    assert body["model"]["model_source"] in ("mlflow", "file", "synthetic_default")
