"""Unit tests for TGN forecaster CSV snapshot fallback (no Neo4j)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.forecasting.tgn_forecaster import TGNForecaster


@pytest.fixture
def snapshot_csv(tmp_path, monkeypatch):
    """Write a minimal supplier snapshot and point SNAPSHOT_DIR at it."""
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    csv_path = snapshot_dir / "supplier_snapshot_20260613.csv"
    csv_path.write_text(
        "supplier_id,name,risk_score,events,max_severity\n"
        "supplier-alpha,Alpha Corp,0.72,3,0.85\n"
        "supplier-beta,Beta Ltd,0.41,0,\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SNAPSHOT_DIR", str(snapshot_dir))
    return csv_path


def test_historical_from_csv_when_neo4j_raises(snapshot_csv) -> None:
    forecaster = TGNForecaster()

    with patch("src.graph.get_neo4j_client", side_effect=ConnectionError("neo4j unavailable")):
        scores = forecaster._get_historical_from_graph("supplier-alpha")

    assert len(scores) == 14
    assert scores[-1] >= 0.7
    assert scores[0] >= 0.5


def test_predict_uses_csv_fallback_without_neo4j(snapshot_csv) -> None:
    forecaster = TGNForecaster()

    with patch("src.graph.get_neo4j_client", side_effect=ConnectionError("neo4j unavailable")):
        forecast = forecaster.predict("supplier-alpha", "supplier", horizon_days=7)

    assert forecast.entity_id == "supplier-alpha"
    assert forecast.predicted_risk_score != 0.5
    assert "insufficient_data" not in forecast.detected_patterns


def test_csv_fallback_missing_supplier_returns_empty(tmp_path, monkeypatch) -> None:
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "supplier_snapshot_20260613.csv").write_text(
        "supplier_id,name,risk_score,events,max_severity\n"
        "supplier-alpha,Alpha Corp,0.72,3,0.85\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SNAPSHOT_DIR", str(snapshot_dir))

    forecaster = TGNForecaster()
    with patch("src.graph.get_neo4j_client", side_effect=ConnectionError("neo4j unavailable")):
        scores = forecaster._get_historical_from_graph("unknown-supplier")

    assert scores == []


def test_load_supplier_snapshot_row_picks_latest(tmp_path, monkeypatch) -> None:
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "supplier_snapshot_20260601.csv").write_text(
        "supplier_id,name,risk_score,events,max_severity\n"
        "supplier-alpha,Old,0.30,0,\n",
        encoding="utf-8",
    )
    (snapshot_dir / "supplier_snapshot_20260613.csv").write_text(
        "supplier_id,name,risk_score,events,max_severity\n"
        "supplier-alpha,New,0.80,2,0.9\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SNAPSHOT_DIR", str(snapshot_dir))

    forecaster = TGNForecaster()
    row = forecaster._load_supplier_snapshot_row("supplier-alpha")

    assert row is not None
    assert row["name"] == "New"
    assert float(row["risk_score"]) == 0.8
