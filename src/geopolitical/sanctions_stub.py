"""OpenSanctions-style demo entities for portfolio map layer."""

from __future__ import annotations

from typing import Any, Dict, List

SANCTIONED_ENTITIES: List[Dict[str, Any]] = [
    {
        "id": "sanction-ru-energy-001",
        "name": "Rosneft Trading Division",
        "country": "RU",
        "latitude": 55.75,
        "longitude": 37.62,
        "program": "Energy sector sanctions",
        "severity": 0.85,
        "sectors": ["energy"],
    },
    {
        "id": "sanction-ir-shipping-001",
        "name": "IRISL Shipping Group",
        "country": "IR",
        "latitude": 27.18,
        "longitude": 56.28,
        "program": "Maritime sanctions",
        "severity": 0.9,
        "sectors": ["shipping", "energy"],
    },
    {
        "id": "sanction-cn-tech-001",
        "name": "Advanced Chip Export Entity",
        "country": "CN",
        "latitude": 31.23,
        "longitude": 121.47,
        "program": "US export controls",
        "severity": 0.78,
        "sectors": ["semiconductors"],
    },
]


def sanctions_geojson() -> Dict[str, Any]:
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [e["longitude"], e["latitude"]],
            },
            "properties": {
                "id": e["id"],
                "name": e["name"],
                "country": e["country"],
                "program": e["program"],
                "severity": e["severity"],
                "sectors": e["sectors"],
            },
        }
        for e in SANCTIONED_ENTITIES
    ]
    return {"type": "FeatureCollection", "features": features, "metadata": {"count": len(features)}}
