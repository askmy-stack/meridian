"""Unit tests for vessel loader event mapping."""

from __future__ import annotations

from src.consumers.vessel_loader import vessel_event_to_props


def test_vessel_event_to_props_maps_chokepoint() -> None:
    payload = {
        "event_id": "ais_123_1",
        "event_type": "chokepoint_transit",
        "mmsi": "366123456",
        "vessel_name": "MSC TEST",
        "location": {"latitude": 12.5, "longitude": 43.3},
        "speed": 10.5,
        "raw_data": {"in_chokepoint": "Bab el-Mandeb"},
    }
    props = vessel_event_to_props(payload)
    assert props is not None
    assert props["mmsi"] == "366123456"
    assert props["chokepoint_name"] == "Bab el-Mandeb"
    assert props["latitude"] == 12.5


def test_vessel_event_to_props_skips_missing_geo() -> None:
    assert vessel_event_to_props({"mmsi": "1"}) is None
