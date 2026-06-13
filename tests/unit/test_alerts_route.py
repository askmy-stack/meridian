"""Unit tests for the /alerts FastAPI router.

These run without Neo4j or Kafka because the alert history is in-memory.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    """Build a TestClient with a fresh alerting service per test."""
    httpx = pytest.importorskip("httpx")  # noqa: F841
    fastapi_testclient = pytest.importorskip("fastapi.testclient")

    from src.alerting import slack as slack_mod
    slack_mod._service = None  # type: ignore[attr-defined]

    from src.api import main as main_mod
    importlib.reload(main_mod)

    yield fastapi_testclient.TestClient(main_mod.app)


def test_list_alerts_empty(client) -> None:
    """Empty history returns total=0, alerts=[]."""
    resp = client.get("/alerts?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["alerts"] == []


def test_post_test_alert_then_list(client) -> None:
    """A test alert appears in the list after being emitted."""
    resp = client.post(
        "/alerts/test",
        params={"title": "unit-test-alert", "message": "synthetic", "tier": "warning"},
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["sent"] is True
    assert payload["alert"]["tier"] == "warning"

    listed = client.get("/alerts").json()
    assert listed["total"] >= 1
    assert any(a["title"] == "unit-test-alert" for a in listed["alerts"])


def test_invalid_tier_filter_rejected(client) -> None:
    resp = client.get("/alerts?tier=nope")
    assert resp.status_code == 400
    assert "Invalid tier" in resp.json()["detail"]


def test_test_alert_blocked_in_production(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    resp = client.post("/alerts/test")
    assert resp.status_code == 403
