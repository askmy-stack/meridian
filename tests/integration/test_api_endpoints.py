"""Integration tests for FastAPI endpoints.

Requires Docker Compose stack to be running:
    docker compose up -d

These tests only assert HTTP-level behavior; they do not assume any
particular Neo4j data has been seeded.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def client():
    pytest.importorskip("httpx")
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from src.api.main import app
    return fastapi_testclient.TestClient(app)


def test_health(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_health_neo4j(client, neo4j_required) -> None:  # noqa: ARG001
    resp = client.get("/health/neo4j")
    assert resp.status_code in (200, 503)


def test_cors_not_wildcard(client) -> None:
    """CORS must reflect a specific origin, never '*' (B-04 regression test)."""
    resp = client.options(
        "/health",
        headers={
            "Origin": "https://malicious.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Preflight from a non-allowlisted origin must not produce '*'
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert allow_origin != "*"


def test_alerts_endpoint_exists(client) -> None:
    """B-11 regression: /alerts must not 404."""
    resp = client.get("/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert "alerts" in body and "total" in body


def test_supplier_explanation_endpoint_handles_missing_supplier(
    client, neo4j_required  # noqa: ARG001
) -> None:
    """Regression: /suppliers/{id}/explanation must not raise unhandled 500."""
    resp = client.get("/suppliers/__nonexistent_supplier__/explanation")
    assert resp.status_code in (200, 404, 422, 503)
