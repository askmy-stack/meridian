"""Shared helpers for Event → Supplier :AFFECTS edge metadata.

Documented link methods (Phase A):
    geospatial    — event coordinates within radius of supplier
    country_match — event.country equals supplier.country_iso
    demo_seed     — curated demo scenarios (seed_demo_scenarios.py)
    manual        — fuzzy NER / text entity resolution
"""

from __future__ import annotations

from typing import Any, Optional

# Canonical link methods exposed in graph health / API docs
LINK_METHODS = frozenset({"geospatial", "country_match", "demo_seed", "manual"})


def affects_merge_cypher(*, link_method: str, confidence: float) -> str:
    """Return Cypher MERGE fragment setting standard AFFECTS edge properties."""
    if link_method not in LINK_METHODS:
        raise ValueError(f"Unknown link_method: {link_method!r}")
    conf = max(0.0, min(1.0, confidence))
    return f"""
        MERGE (e)-[r:AFFECTS]->(s)
        ON CREATE SET
            r.link_method = '{link_method}',
            r.confidence = {conf},
            r.linked_at = datetime()
        ON MATCH SET
            r.link_method = coalesce(r.link_method, '{link_method}'),
            r.confidence = CASE
                WHEN r.confidence IS NULL OR {conf} > r.confidence THEN {conf}
                ELSE r.confidence
            END,
            r.linked_at = coalesce(r.linked_at, datetime())
    """


def link_event_to_suppliers_by_country(
    neo4j_client: Any,
    event_id: str,
    country: Optional[str],
    *,
    confidence: float = 0.55,
) -> int:
    """Create country_match AFFECTS edges for all suppliers in the event country."""
    if not country:
        return 0

    merge = affects_merge_cypher(link_method="country_match", confidence=confidence)
    query = f"""
        MATCH (e:Event {{id: $event_id}})
        MATCH (s:Supplier)
        WHERE s.country_iso = toUpper($country)
        {merge}
        RETURN count(r) AS linked
    """
    rows = neo4j_client.execute_query(
        query,
        {"event_id": event_id, "country": country.upper()},
    )
    return int(rows[0].get("linked", 0) if rows else 0)


def link_event_to_suppliers_by_geospatial(
    neo4j_client: Any,
    event_id: str,
    *,
    radius_km: float = 250.0,
    base_confidence: float = 0.7,
) -> int:
    """Create geospatial AFFECTS edges for suppliers within radius of the event."""
    merge = affects_merge_cypher(link_method="geospatial", confidence=base_confidence)
    query = f"""
        MATCH (e:Event {{id: $event_id}})
        WHERE e.latitude IS NOT NULL AND e.longitude IS NOT NULL
        MATCH (s:Supplier)
        WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
        WITH e, s,
             point({{latitude: e.latitude, longitude: e.longitude}}) AS ep,
             point({{latitude: s.latitude, longitude: s.longitude}}) AS sp
        WHERE point.distance(ep, sp) <= $radius_m
        {merge}
        RETURN count(r) AS linked
    """
    rows = neo4j_client.execute_query(
        query,
        {"event_id": event_id, "radius_m": radius_km * 1000.0},
    )
    return int(rows[0].get("linked", 0) if rows else 0)
