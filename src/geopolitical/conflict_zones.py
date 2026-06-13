"""Static geopolitical conflict and tension zones for map visualization.

Coordinates are approximate operational areas for portfolio demo — not classified intel.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


def _circle_polygon(
    lon: float,
    lat: float,
    radius_km: float,
    points: int = 32,
) -> List[List[float]]:
    """Approximate a circle on the sphere as a GeoJSON ring [lon, lat]."""
    ring: List[List[float]] = []
    lat_rad = math.radians(lat)
    for i in range(points + 1):
        bearing = 2 * math.pi * i / points
        d_lat = (radius_km / 6371.0) * math.cos(bearing)
        d_lon = (radius_km / 6371.0) * math.sin(bearing) / max(math.cos(lat_rad), 0.01)
        ring.append([lon + math.degrees(d_lon), lat + math.degrees(d_lat)])
    return ring


CONFLICT_ZONES: List[Dict[str, Any]] = [
    {
        "id": "zone-ukraine",
        "name": "Russia–Ukraine Conflict",
        "category": "armed_conflict",
        "severity": 0.92,
        "center": [31.5, 49.0],
        "radius_km": 420,
        "countries": ["UA", "RU"],
        "summary": "Active land war disrupting grain, metals, and EU border logistics.",
        "sectors": ["agriculture", "metals", "energy"],
    },
    {
        "id": "zone-red-sea",
        "name": "Red Sea / Bab-el-Mandeb",
        "category": "maritime_disruption",
        "severity": 0.78,
        "center": [43.0, 14.5],
        "radius_km": 380,
        "countries": ["YE", "ER", "DJ", "SA"],
        "summary": "Shipping attacks and reroutes via Cape of Good Hope extend Asia–EU lead times.",
        "sectors": ["container_shipping", "retail"],
    },
    {
        "id": "zone-taiwan-strait",
        "name": "Taiwan Strait Tension",
        "category": "geopolitical_tension",
        "severity": 0.88,
        "center": [119.5, 24.0],
        "radius_km": 280,
        "countries": ["TW", "CN"],
        "summary": "Semiconductor chokepoint risk for advanced fabs and transpacific lanes.",
        "sectors": ["semiconductors", "electronics"],
    },
    {
        "id": "zone-hormuz",
        "name": "Strait of Hormuz / US–Iran Tensions",
        "category": "energy_security",
        "severity": 0.82,
        "center": [56.3, 26.5],
        "radius_km": 320,
        "countries": ["IR", "OM", "AE", "SA"],
        "summary": "Energy corridor exposure; tanker insurance premiums and delay risk elevated.",
        "sectors": ["energy", "chemicals"],
    },
    {
        "id": "zone-suez",
        "name": "Suez Canal Corridor",
        "category": "chokepoint_congestion",
        "severity": 0.65,
        "center": [32.35, 30.0],
        "radius_km": 200,
        "countries": ["EG"],
        "summary": "Canal transit backlog ripples through Mediterranean and Indian Ocean schedules.",
        "sectors": ["shipping", "manufacturing"],
    },
    {
        "id": "zone-china-us-trade",
        "name": "China–US Trade Restrictions",
        "category": "trade_policy",
        "severity": 0.7,
        "center": [116.4, 35.0],
        "radius_km": 900,
        "countries": ["CN", "US"],
        "summary": "Export controls and tariffs on chips, batteries, and critical minerals.",
        "sectors": ["semiconductors", "ev_batteries", "rare_earths"],
    },
]


def conflict_zones_geojson() -> Dict[str, Any]:
    """Return conflict zones as GeoJSON FeatureCollection."""
    features = []
    for zone in CONFLICT_ZONES:
        lon, lat = zone["center"]
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [_circle_polygon(lon, lat, zone["radius_km"])],
            },
            "properties": {
                "id": zone["id"],
                "name": zone["name"],
                "category": zone["category"],
                "severity": zone["severity"],
                "countries": zone["countries"],
                "summary": zone["summary"],
                "sectors": zone["sectors"],
            },
        })
    return {"type": "FeatureCollection", "features": features}
