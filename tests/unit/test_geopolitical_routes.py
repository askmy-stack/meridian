"""Unit tests for geopolitical intelligence API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_conflict_zones_returns_geojson() -> None:
    response = client.get("/geopolitical/conflict-zones")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) >= 6
    props = body["features"][0]["properties"]
    assert "name" in props
    assert "severity" in props
    assert "summary" in props


def test_map_layers_includes_zones_without_neo4j_events() -> None:
    response = client.get(
        "/geopolitical/map-layers",
        params={"include_events": False, "include_routes": False, "entity_type": "supplier"},
    )
    assert response.status_code == 200
    layers = response.json()["layers"]
    assert "conflict_zones" in layers
    assert layers["conflict_zones"]["metadata"]["count"] >= 6


@pytest.mark.neo4j_required
def test_geopolitical_events_after_seed() -> None:
    response = client.get("/geopolitical/events", params={"days": 30})
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["metadata"]["count"] >= 1


@pytest.mark.neo4j_required
def test_trade_routes_after_seed() -> None:
    response = client.get("/geopolitical/trade-routes", params={"limit": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["count"] >= 1
    feature = body["features"][0]
    assert feature["geometry"]["type"] == "LineString"


@pytest.mark.neo4j_required
def test_event_timeline_after_seed() -> None:
    response = client.get("/geopolitical/timeline", params={"days": 30})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert "title" in body["events"][0]
