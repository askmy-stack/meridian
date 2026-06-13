"""Shared pytest fixtures for Meridian.

Conventions:
    - tests/unit/        : no external services required (mock everything)
    - tests/integration/ : requires `docker compose up -d` (Neo4j + Kafka)

Run a subset:
    pytest tests/unit/        # fast lane
    pytest tests/integration/ # full stack
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _set_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ENVIRONMENT=test so security guards stay strict but predictable."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    # Stable JWT key for tests (does not match prod requirements; testing only)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-do-not-use-in-prod-x" * 2)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    # Align with docker-compose host port mapping (7688) when not set by CI
    if not os.getenv("NEO4J_URI"):
        monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7688")
    if not os.getenv("NEO4J_PASSWORD"):
        monkeypatch.setenv("NEO4J_PASSWORD", "meridian_password")


@pytest.fixture(autouse=True)
def _neo4j_marker_skip(request: pytest.FixtureRequest) -> None:
    """Skip tests marked neo4j_required when graph is unavailable."""
    if request.node.get_closest_marker("neo4j_required") is None:
        return
    try:
        from src.graph import get_neo4j_client
        if not get_neo4j_client().health_check():
            pytest.skip("Neo4j not reachable; start `docker compose up -d` and `make seed-all`")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Neo4j client unavailable: {exc}")


@pytest.fixture
def neo4j_required() -> None:
    """Skip a test if Neo4j is not reachable."""
    try:
        from src.graph import get_neo4j_client
        client = get_neo4j_client()
        if not client.health_check():
            pytest.skip("Neo4j not reachable; start `docker compose up -d`")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Neo4j client unavailable: {exc}")
