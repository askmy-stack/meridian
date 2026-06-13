"""Unit tests for static conflict zone reference data."""

from src.geopolitical.conflict_zones import CONFLICT_ZONES, conflict_zones_geojson


def test_conflict_zone_count() -> None:
    assert len(CONFLICT_ZONES) >= 6


def test_conflict_zones_include_ukraine_and_taiwan() -> None:
    ids = {z["id"] for z in CONFLICT_ZONES}
    assert "zone-ukraine" in ids
    assert "zone-taiwan-strait" in ids
    assert "zone-china-us-trade" in ids


def test_geojson_valid_structure() -> None:
    data = conflict_zones_geojson()
    assert data["type"] == "FeatureCollection"
    for feature in data["features"]:
        assert feature["geometry"]["type"] == "Polygon"
        assert len(feature["geometry"]["coordinates"][0]) >= 4
