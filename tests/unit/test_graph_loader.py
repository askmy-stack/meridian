"""Unit tests for graph loader event mapping."""

from __future__ import annotations

from src.consumers.graph_loader import (
    build_event_title,
    estimate_severity,
    kafka_event_to_graph_props,
)


def test_estimate_severity_from_goldstein() -> None:
    event = {"raw_data": {"GoldsteinScale": "-8.5"}, "event_type": "conflict"}
    assert estimate_severity(event) == 0.85


def test_kafka_event_to_graph_props_maps_coordinates() -> None:
    payload = {
        "event_id": "gdelt_999",
        "event_type": "protest",
        "source": "gdelt",
        "description": "Port workers strike near Suez",
        "country": "Egypt",
        "region": "Suez",
        "location": {"latitude": 30.0, "longitude": 32.3},
        "actors": ["Port Union"],
    }
    props = kafka_event_to_graph_props(payload)
    assert props is not None
    assert props["id"] == "gdelt_999"
    assert props["latitude"] == 30.0
    assert props["severity"] >= 0.5
    assert "Suez" in props["title"] or "protest" in props["title"].lower()


def test_kafka_event_to_graph_props_skips_missing_geo() -> None:
    assert kafka_event_to_graph_props({"event_id": "x"}) is None


def test_build_event_title_with_actors() -> None:
    title = build_event_title(
        {"event_type": "conflict", "actors": ["Houthi"], "region": "Red Sea"}
    )
    assert "Houthi" in title
