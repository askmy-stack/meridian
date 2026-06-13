#!/usr/bin/env python3
"""Seed Route topology: (Port)-[:ON_ROUTE]->(Route)-[:PASSES_THROUGH]->(Chokepoint).

Run after `make seed` (ports + chokepoints). Idempotent MERGE operations.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import get_neo4j_client

logger = structlog.get_logger(__name__)

# (locode, sequence, is_origin, is_destination)
PortStop = Tuple[str, int, bool, bool]
# (chokepoint_name, sequence)
ChokepointStop = Tuple[str, int]

ROUTES: List[dict] = [
    {
        "id": "route-asia-europe-suez",
        "name": "Asia → Europe via Suez",
        "origin_region": "East Asia",
        "destination_region": "North Europe",
        "avg_transit_days": 28,
        "ports": [
            ("CNSHG", 0, True, False),
            ("SGSIN", 1, False, False),
            ("NLRTM", 2, False, True),
        ],
        "chokepoints": [
            ("Strait of Malacca", 0),
            ("Suez Canal", 1),
        ],
    },
    {
        "id": "route-asia-uswest-panama",
        "name": "Asia → US West Coast via Panama",
        "origin_region": "East Asia",
        "destination_region": "US West Coast",
        "avg_transit_days": 18,
        "ports": [
            ("CNSHG", 0, True, False),
            ("USLAX", 1, False, True),
        ],
        "chokepoints": [
            ("Strait of Malacca", 0),
            ("Panama Canal", 1),
        ],
    },
    {
        "id": "route-gulf-europe-bab",
        "name": "Gulf → Europe via Bab-el-Mandeb",
        "origin_region": "Middle East",
        "destination_region": "North Europe",
        "avg_transit_days": 22,
        "ports": [
            ("AEJEA", 0, True, False),
            ("NLRTM", 1, False, True),
        ],
        "chokepoints": [
            ("Strait of Hormuz", 0),
            ("Bab-el-Mandeb", 1),
            ("Suez Canal", 2),
        ],
    },
    {
        "id": "route-asia-taiwan-strait",
        "name": "Taiwan Strait feeder",
        "origin_region": "East Asia",
        "destination_region": "East Asia",
        "avg_transit_days": 5,
        "ports": [
            ("TWKHH", 0, True, False),
            ("CNSHG", 1, False, True),
        ],
        "chokepoints": [
            ("Taiwan Strait", 0),
        ],
    },
]


def seed_routes() -> dict:
    """Create Route nodes and ON_ROUTE / PASSES_THROUGH relationships."""
    client = get_neo4j_client()
    routes_created = 0
    on_route_links = 0
    chokepoint_links = 0

    route_query = """
    MERGE (r:Route {id: $id})
    SET r.name = $name,
        r.origin_region = $origin_region,
        r.destination_region = $destination_region,
        r.avg_transit_days = $avg_transit_days
    RETURN r.id AS id
    """

    on_route_query = """
    MATCH (r:Route {id: $route_id})
    MATCH (p:Port {locode: $locode})
    MERGE (p)-[rel:ON_ROUTE]->(r)
    SET rel.sequence = $sequence,
        rel.is_origin = $is_origin,
        rel.is_destination = $is_destination
    RETURN count(rel) AS linked
    """

    passes_through_query = """
    MATCH (r:Route {id: $route_id})
    MATCH (c:Chokepoint {name: $chokepoint_name})
    MERGE (r)-[rel:PASSES_THROUGH]->(c)
    SET rel.sequence = $sequence
    RETURN count(rel) AS linked
    """

    for route in ROUTES:
        client.execute_query(
            route_query,
            {
                "id": route["id"],
                "name": route["name"],
                "origin_region": route["origin_region"],
                "destination_region": route["destination_region"],
                "avg_transit_days": route.get("avg_transit_days"),
            },
        )
        routes_created += 1

        for locode, sequence, is_origin, is_destination in route["ports"]:
            rows = client.execute_query(
                on_route_query,
                {
                    "route_id": route["id"],
                    "locode": locode,
                    "sequence": sequence,
                    "is_origin": is_origin,
                    "is_destination": is_destination,
                },
            )
            if rows:
                on_route_links += 1

        for chokepoint_name, sequence in route["chokepoints"]:
            rows = client.execute_query(
                passes_through_query,
                {
                    "route_id": route["id"],
                    "chokepoint_name": chokepoint_name,
                    "sequence": sequence,
                },
            )
            if rows:
                chokepoint_links += 1

    result = {
        "routes_created": routes_created,
        "on_route_links": on_route_links,
        "route_chokepoint_links": chokepoint_links,
    }
    logger.info("routes_seeded", **result)
    return result


def main() -> int:
    load_dotenv()
    print("Meridian route topology seeder")
    print("=" * 40)
    result = seed_routes()
    print(f"Routes: {result['routes_created']}")
    print(f"Port ON_ROUTE links: {result['on_route_links']}")
    print(f"Route PASSES_THROUGH links: {result['route_chokepoint_links']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
