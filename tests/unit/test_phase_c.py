"""Unit tests for Phase C API routes (no Neo4j)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_regime_summary_endpoint() -> None:
    response = client.get("/analytics/regime-summary?days=14")
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
    assert data["summary"]["total"] >= 1


def test_region_regime_endpoint() -> None:
    response = client.get("/intelligence/regions/zone-ukraine/regime")
    assert response.status_code == 200
    data = response.json()
    assert data["region_id"] == "zone-ukraine"
    assert data["regime"] in ("stable", "escalation", "crisis")


def test_backtest_summary_not_run() -> None:
    with patch("src.api.routes.analytics.BACKTEST_JSON", Path("/nonexistent/backtest.json")):
        response = client.get("/analytics/backtest-summary")
    assert response.status_code == 200
    assert response.json()["status"] == "not_run"


def test_backtest_summary_with_file(tmp_path) -> None:
    backtest_file = tmp_path / "latest.json"
    backtest_file.write_text(
        json.dumps({"status": "ok", "precision_at_k": 0.6, "recall": 0.5}),
        encoding="utf-8",
    )
    with patch("src.api.routes.analytics.BACKTEST_JSON", backtest_file):
        response = client.get("/analytics/backtest-summary")
    assert response.status_code == 200
    assert response.json()["precision_at_k"] == 0.6


def test_supplier_alternatives_graceful() -> None:
    with patch(
        "src.intelligence.graph_embeddings.rank_alternative_suppliers",
        return_value=[],
    ):
        response = client.get("/suppliers/demo-supplier/alternatives")
    assert response.status_code == 200
    assert response.json()["alternatives"] == []
