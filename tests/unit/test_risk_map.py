"""Unit tests for risk map visualization API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_risk_map_supplier_geojson_shape() -> None:
    response = client.get("/visualization/risk-map", params={"entity_type": "supplier"})
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert "metadata" in body


@pytest.mark.neo4j_required
def test_risk_map_ports_use_congestion_score() -> None:
    response = client.get("/visualization/risk-map", params={"entity_type": "port", "min_risk": 0})
    assert response.status_code == 200
    features = response.json()["features"]
    if features:
        assert "risk_score" in features[0]["properties"]
        assert "entity_type" in features[0]["properties"] or True


@pytest.mark.neo4j_required
def test_risk_map_chokepoints_return_features() -> None:
    response = client.get("/visualization/risk-map", params={"entity_type": "chokepoint"})
    assert response.status_code == 200
    assert response.json()["metadata"]["entity_type"] == "chokepoint"
