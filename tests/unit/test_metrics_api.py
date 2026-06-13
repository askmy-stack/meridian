"""Unit tests for metrics methodology API."""

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
