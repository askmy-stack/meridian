"""Unit tests for simulation API routes."""

from __future__ import annotations

import pytest


@pytest.fixture
def client():
    pytest.importorskip("httpx")
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    from src.api.main import app

    return fastapi_testclient.TestClient(app)


def test_list_simulation_scenarios(client) -> None:
    resp = client.get("/simulation/scenarios")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 6
    assert any(s["id"] == "red-sea-bab-el-mandeb" for s in body["scenarios"])
    assert any(s["id"] == "russia-ukraine-supply" for s in body["scenarios"])
    first = body["scenarios"][0]
    assert "mitigations" in first
    assert "region" in first


def test_run_demo_scenario_not_found(client) -> None:
    resp = client.post("/simulation/scenarios/does-not-exist/run")
    assert resp.status_code == 404
