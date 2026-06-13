"""NOAA weather alert demo layer — static severe-weather zones affecting ports."""

from __future__ import annotations

from typing import Any, Dict, List

WEATHER_ALERTS: List[Dict[str, Any]] = [
    {
        "id": "noaa-gulf-cyclone",
        "title": "Tropical storm watch — US Gulf Coast",
        "severity": 0.72,
        "latitude": 28.5,
        "longitude": -89.5,
        "radius_km": 350,
        "affected_ports": ["USHOU", "USMSY"],
        "summary": "Port closure risk for Houston and New Orleans chemical exports.",
    },
    {
        "id": "noaa-med-storm",
        "title": "Mediterranean gale warning",
        "severity": 0.58,
        "latitude": 36.0,
        "longitude": 15.0,
        "radius_km": 280,
        "affected_ports": ["EGPSD", "GRPIR"],
        "summary": "Berth delays likely at eastern Mediterranean hubs.",
    },
]


def weather_alerts_geojson() -> Dict[str, Any]:
    import math

    def ring(lon: float, lat: float, km: float, n: int = 24) -> List[List[float]]:
        pts: List[List[float]] = []
        lat_r = math.radians(lat)
        for i in range(n + 1):
            b = 2 * math.pi * i / n
            d_lat = (km / 6371.0) * math.cos(b)
            d_lon = (km / 6371.0) * math.sin(b) / max(math.cos(lat_r), 0.01)
            pts.append([lon + math.degrees(d_lon), lat + math.degrees(d_lat)])
        return pts

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring(a["longitude"], a["latitude"], a["radius_km"])],
            },
            "properties": {
                "id": a["id"],
                "title": a["title"],
                "severity": a["severity"],
                "summary": a["summary"],
                "affected_ports": a["affected_ports"],
            },
        }
        for a in WEATHER_ALERTS
    ]
    return {"type": "FeatureCollection", "features": features, "metadata": {"count": len(features)}}
