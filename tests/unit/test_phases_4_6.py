"""Unit tests for analytics API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


@pytest.fixture
def mock_neo4j():
    with patch("src.api.routes.analytics.get_neo4j_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client


def test_sector_dashboard_returns_sectors(mock_neo4j: MagicMock) -> None:
    mock_neo4j.execute_query.return_value = [
        {
            "id": "sup-1",
            "name": "Taiwan Semiconductor Fab",
            "industry": "semiconductors",
            "country": "TW",
            "risk": 0.82,
            "critical": True,
        },
        {
            "id": "sup-2",
            "name": "Rotterdam Energy Terminal",
            "industry": "energy",
            "country": "NL",
            "risk": 0.55,
            "critical": False,
        },
    ]
    response = client.get("/analytics/sectors")
    assert response.status_code == 200
    body = response.json()
    assert "sectors" in body
    assert len(body["sectors"]) == 4
    semi = next(s for s in body["sectors"] if s["sector"] == "semiconductors")
    assert semi["supplier_count"] >= 1


def test_graph_health_report(mock_neo4j: MagicMock) -> None:
    mock_neo4j.execute_query.side_effect = [
        [{"suppliers": 30, "suppliers_missing_geo": 2}],
        [{"suppliers_without_ports": 5}],
        [{"event_count": 8}],
        [{"suppliers_with_events": 12}],
        [{"tier2_link_count": 6}],
        [{"avg_link_confidence": 0.72, "affects_with_confidence": 15}],
    ]
    response = client.get("/analytics/graph/health")
    assert response.status_code == 200
    body = response.json()
    assert body["suppliers"] == 30
    assert body["tier2_link_count"] == 6
    assert body["avg_link_confidence"] == 0.72
    assert body["affects_with_confidence"] == 15
    assert 0.0 <= body["completeness_score"] <= 1.0
    assert body["status"] == "healthy"


def test_weather_layer() -> None:
    response = client.get("/intelligence/layers/weather")
    assert response.status_code == 200
    assert response.json()["type"] == "FeatureCollection"


def test_sanctions_layer() -> None:
    response = client.get("/intelligence/layers/sanctions")
    assert response.status_code == 200
    assert response.json()["type"] == "FeatureCollection"


def test_copilot_maps_red_sea() -> None:
    with patch("src.api.routes.intelligence_extended.get_neo4j_client") as mock_get:
        mock_get.return_value.execute_query.side_effect = [
            [{"name": "Fab A", "risk": 0.9}],
            [{"suppliers": 10, "events": 4, "affected": 3}],
        ]
        response = client.post(
            "/intelligence/copilot",
            json={"question": "What if Red Sea shipping is attacked?"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["suggested_scenario_id"] == "red-sea-bab-el-mandeb"
    assert body["grounded"] is True
    assert body["disclaimer"]


def test_simulation_compare_requires_two_ids() -> None:
    with patch("src.api.routes.simulation.propagate_disruption") as mock_prop, patch(
        "src.api.routes.simulation.simulate_disruption"
    ) as mock_sim, patch(
        "src.api.routes.simulation._build_map_overlay",
        return_value={
            "epicenter": None,
            "affected_suppliers": {"type": "FeatureCollection", "features": []},
            "region": "test",
            "timeline_projection_days": 0,
        },
    ):
        mock_prop.return_value.to_dict.return_value = {
            "suppliers_affected": 3,
            "revenue_at_risk": 1000,
            "recovery_time_days": 14,
        }
        mock_sim.return_value.to_dict.return_value = {
            "disruption_probability": 0.4,
            "expected_duration_days": 10,
        }
        response = client.post(
            "/simulation/compare",
            json={"scenario_ids": ["red-sea-bab-el-mandeb", "suez-canal-blockage"]},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["comparisons"]) == 2
    assert body["highest_impact"] is not None
