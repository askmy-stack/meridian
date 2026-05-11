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
