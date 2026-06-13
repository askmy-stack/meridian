"""Geopolitical intelligence API — events, conflict zones, trade routes, unified map layers."""

from __future__ import annotations

from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from ...geopolitical.conflict_zones import conflict_zones_geojson
from ...graph import get_neo4j_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/geopolitical", tags=["Geopolitical"])


def _risk_category(score: float) -> str:
    if score is None:
        return "UNKNOWN"
    if score < 0.4:
        return "LOW"
    if score < 0.6:
        return "MEDIUM"
    if score < 0.8:
        return "HIGH"
    return "CRITICAL"


def build_conflict_zones_payload() -> dict:
    """Return conflict zones GeoJSON (no Neo4j required)."""
    data = conflict_zones_geojson()
    return {
        **data,
        "metadata": {"count": len(data["features"]), "source": "meridian-reference-v1"},
    }


def build_geopolitical_events_payload(
    days: int = 30,
    event_type: Optional[str] = None,
) -> dict:
    """Load active events as GeoJSON features."""
    client = get_neo4j_client()
    query = """
    MATCH (e:Event)
    WHERE e.resolved_at > datetime() - duration($window)
    OPTIONAL MATCH (e)-[:AFFECTS]->(s:Supplier)
    WITH e, head(collect(s)) AS s
    ORDER BY e.severity DESC
    RETURN e.id AS id,
           e.event_type AS event_type,
           e.title AS title,
           e.description AS description,
           e.severity AS severity,
           coalesce(e.longitude, s.longitude) AS lon,
           coalesce(e.latitude, s.latitude) AS lat,
           s.name AS supplier_name,
           s.country_iso AS country
    LIMIT 100
    """
    rows = client.execute_query(query, {"window": f"P{days}D"})

    features = []
    for row in rows:
        if event_type and row.get("event_type") != event_type:
            continue
        lon, lat = row.get("lon"), row.get("lat")
        if lon is None or lat is None:
            continue
        severity = float(row.get("severity") or 0.5)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "id": row["id"],
                "event_type": row.get("event_type"),
                "title": row.get("title"),
                "description": row.get("description"),
                "severity": severity,
                "risk_category": _risk_category(severity),
                "supplier_name": row.get("supplier_name"),
                "country": row.get("country"),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {"count": len(features), "window_days": days},
    }


def build_trade_routes_payload(limit: int = 120) -> dict:
    """Load supplier→port and port→chokepoint segments as GeoJSON lines."""
    client = get_neo4j_client()
    query = """
    MATCH (s:Supplier)-[:SHIPS_VIA]->(p:Port)
    WHERE s.latitude IS NOT NULL AND p.latitude IS NOT NULL
    RETURN s.id AS source_id, s.name AS source_name,
           p.id AS target_id, p.name AS target_name,
           s.longitude AS s_lon, s.latitude AS s_lat,
           p.longitude AS p_lon, p.latitude AS p_lat,
           coalesce(s.risk_score, 0) AS risk_score,
           'SHIPS_VIA' AS route_type
    LIMIT $limit
    UNION
    MATCH (p:Port)-[:PASSES_THROUGH]->(c:Chokepoint)
    WHERE p.latitude IS NOT NULL AND c.latitude IS NOT NULL
    RETURN p.id AS source_id, p.name AS source_name,
           c.id AS target_id, c.name AS target_name,
           p.longitude AS s_lon, p.latitude AS s_lat,
           c.longitude AS p_lon, c.latitude AS p_lat,
           coalesce(c.current_risk_score, 0) AS risk_score,
           'PASSES_THROUGH' AS route_type
    LIMIT $limit
    """
    rows = client.execute_query(query, {"limit": limit})

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [row["s_lon"], row["s_lat"]],
                    [row["p_lon"], row["p_lat"]],
                ],
            },
            "properties": {
                "source_id": row["source_id"],
                "source_name": row["source_name"],
                "target_id": row["target_id"],
                "target_name": row["target_name"],
                "route_type": row["route_type"],
                "risk_score": row.get("risk_score", 0),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {"count": len(features)},
    }


def build_event_timeline_payload(days: int = 30) -> dict:
    """Chronological event feed for timeline view."""
    client = get_neo4j_client()
    query = """
    MATCH (e:Event)
    WHERE e.resolved_at > datetime() - duration($window)
    OPTIONAL MATCH (e)-[:AFFECTS]->(s:Supplier)
    WITH e, collect(DISTINCT s.name) AS affected_suppliers
    RETURN e.id AS id,
           e.title AS title,
           e.event_type AS event_type,
           e.severity AS severity,
           e.description AS description,
           e.resolved_at AS occurred_at,
           affected_suppliers
    ORDER BY e.severity DESC
    LIMIT 50
    """
    rows = client.execute_query(query, {"window": f"P{days}D"})
    events: List[dict] = []
    for row in rows:
        occurred = row.get("occurred_at")
        if hasattr(occurred, "to_native"):
            occurred = occurred.to_native().isoformat()
        events.append({
            "id": row["id"],
            "title": row.get("title"),
            "event_type": row.get("event_type"),
            "severity": row.get("severity"),
            "description": row.get("description"),
            "occurred_at": occurred,
            "affected_suppliers": row.get("affected_suppliers") or [],
        })
    return {"events": events, "count": len(events), "window_days": days}


def build_entity_layer(entity_type: str) -> dict:
    """GeoJSON points for suppliers, ports, or chokepoints."""
    client = get_neo4j_client()
    label_map = {"supplier": "Supplier", "port": "Port", "chokepoint": "Chokepoint"}
    label = label_map[entity_type]
    risk_expr = {
        "Supplier": "coalesce(n.risk_score, 0)",
        "Port": "coalesce(n.congestion_score, n.risk_score, 0)",
        "Chokepoint": "coalesce(n.current_risk_score, n.risk_score, 0)",
    }[label]
    query = f"""
    MATCH (n:{label})
    WHERE n.latitude IS NOT NULL AND n.longitude IS NOT NULL
    RETURN n.id AS id, n.name AS name, n.latitude AS lat, n.longitude AS lon,
           {risk_expr} AS risk, n.country_iso AS country
    ORDER BY risk DESC
    LIMIT 500
    """
    rows = client.execute_query(query)
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {
                "id": r["id"],
                "name": r["name"],
                "entity_type": entity_type,
                "risk_score": r["risk"],
                "risk_category": _risk_category(r["risk"]),
                "country": r.get("country"),
            },
        }
        for r in rows
    ]
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {"entity_type": entity_type, "count": len(features)},
    }


def build_map_layers_payload(
    *,
    include_routes: bool = True,
    include_zones: bool = True,
    include_events: bool = True,
    entity_type: str = "supplier",
    event_days: int = 30,
    route_limit: int = 120,
) -> dict:
    """Assemble all map layers — safe for internal use (no FastAPI Query objects)."""
    layers: dict = {}

    if include_zones:
        layers["conflict_zones"] = build_conflict_zones_payload()

    if include_events:
        try:
            layers["events"] = build_geopolitical_events_payload(days=event_days)
        except Exception as exc:
            logger.warning("map_layers_events_skipped", error=str(exc))
            layers["events"] = {"type": "FeatureCollection", "features": [], "metadata": {"count": 0}}

    if include_routes:
        try:
            layers["trade_routes"] = build_trade_routes_payload(limit=route_limit)
        except Exception as exc:
            logger.warning("map_layers_routes_skipped", error=str(exc))
            layers["trade_routes"] = {"type": "FeatureCollection", "features": [], "metadata": {"count": 0}}

    if entity_type == "all":
        layers["entities"] = {
            et: build_entity_layer(et) for et in ("supplier", "port", "chokepoint")
        }
    else:
        layers["entities"] = build_entity_layer(entity_type)

    return {"layers": layers}


@router.get("/conflict-zones")
async def get_conflict_zones() -> dict:
    """GeoJSON polygons for major conflict and tension zones."""
    return build_conflict_zones_payload()


@router.get("/events")
async def get_geopolitical_events(
    days: int = Query(default=30, ge=1, le=365),
    event_type: Optional[str] = None,
) -> dict:
    """Active geopolitical events with coordinates."""
    try:
        return build_geopolitical_events_payload(days=days, event_type=event_type)
    except Exception as exc:
        logger.error("geopolitical_events_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load events: {exc}",
        ) from exc


@router.get("/trade-routes")
async def get_trade_routes(limit: int = Query(default=120, ge=1, le=500)) -> dict:
    """Supply chain shipping lanes as GeoJSON lines."""
    try:
        return build_trade_routes_payload(limit=limit)
    except Exception as exc:
        logger.error("trade_routes_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load trade routes: {exc}",
        ) from exc


@router.get("/timeline")
async def get_event_timeline(days: int = Query(default=30, ge=1, le=365)) -> dict:
    """Chronological geopolitical event feed."""
    try:
        return build_event_timeline_payload(days=days)
    except Exception as exc:
        logger.error("timeline_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load timeline: {exc}",
        ) from exc


@router.get("/map-layers")
async def get_unified_map_layers(
    include_routes: bool = True,
    include_zones: bool = True,
    include_events: bool = True,
    entity_type: str = Query(default="supplier", enum=["supplier", "port", "chokepoint", "all"]),
) -> dict:
    """Single payload for interactive world map."""
    try:
        return build_map_layers_payload(
            include_routes=include_routes,
            include_zones=include_zones,
            include_events=include_events,
            entity_type=entity_type,
        )
    except Exception as exc:
        logger.error("map_layers_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load map layers: {exc}",
        ) from exc
