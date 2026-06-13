#!/usr/bin/env python3
"""Seed demo disruption events and elevate risk for portfolio scenarios.

Creates Event nodes linked to high-risk suppliers so the weekly digest,
timeline, and world map tell a coherent geopolitical story after seed-all.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.client import Neo4jClient

logger = structlog.get_logger(__name__)

DEMO_EVENTS = [
    {
        "id": "evt-red-sea-001",
        "event_type": "maritime_attack",
        "title": "Red Sea shipping disruption",
        "description": "Vessel rerouting via Cape of Good Hope amid Bab-el-Mandeb security incidents.",
        "severity": 0.78,
        "supplier_name": "Rotterdam Components",
        "latitude": 14.5,
        "longitude": 43.0,
        "region": "Red Sea",
    },
    {
        "id": "evt-taiwan-001",
        "event_type": "geopolitical_tension",
        "title": "Taiwan Strait elevated risk",
        "description": "Semiconductor supply concentration risk flagged for transpacific lanes.",
        "severity": 0.88,
        "supplier_name": "Taiwan Semiconductor Corp",
        "latitude": 24.0,
        "longitude": 119.5,
        "region": "Taiwan Strait",
    },
    {
        "id": "evt-suez-001",
        "event_type": "port_congestion",
        "title": "Suez Canal schedule delays",
        "description": "Canal transit backlog affecting EU–Asia component flows.",
        "severity": 0.65,
        "supplier_name": "Istanbul Manufacturing",
        "latitude": 30.0,
        "longitude": 32.35,
        "region": "Suez Canal",
    },
    {
        "id": "evt-hormuz-001",
        "event_type": "conflict_proximity",
        "title": "Strait of Hormuz risk elevation",
        "description": "US–Iran tensions increasing energy and chemical shipping exposure.",
        "severity": 0.82,
        "supplier_name": "Tel Aviv Electronics",
        "latitude": 26.5,
        "longitude": 56.3,
        "region": "Persian Gulf",
    },
    {
        "id": "evt-ukraine-001",
        "event_type": "armed_conflict",
        "title": "Russia–Ukraine war supply shock",
        "description": "Grain, steel, and rail corridors disrupted; EU border logistics strained.",
        "severity": 0.92,
        "supplier_name": "Warsaw Electronics",
        "latitude": 49.0,
        "longitude": 31.5,
        "region": "Eastern Europe",
    },
    {
        "id": "evt-china-us-001",
        "event_type": "trade_restriction",
        "title": "China–US export control escalation",
        "description": "Advanced chip and battery material restrictions widen dual-sourcing gaps.",
        "severity": 0.74,
        "supplier_name": "Acme Electronics Ltd",
        "latitude": 35.0,
        "longitude": 116.4,
        "region": "North Pacific",
    },
    {
        "id": "evt-semiconductor-001",
        "event_type": "supply_shortage",
        "title": "Global semiconductor allocation risk",
        "description": "Lead times extend for automotive and AI accelerator tiers.",
        "severity": 0.8,
        "supplier_name": "Taiwan Semiconductor Corp",
        "latitude": 24.78,
        "longitude": 121.0,
        "region": "Hsinchu",
    },
    {
        "id": "evt-energy-001",
        "event_type": "commodity_shock",
        "title": "Energy price volatility spike",
        "description": "LNG and crude spreads widen; chemical feedstock costs under pressure.",
        "severity": 0.71,
        "supplier_name": "Rotterdam Components",
        "latitude": 51.9,
        "longitude": 4.5,
        "region": "North Sea",
    },
]


def main() -> None:
    load_dotenv()
    client = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "meridian_password"),
    )

    created = 0
    for event in DEMO_EVENTS:
        query = """
        MERGE (e:Event {id: $id})
        SET e.event_type = $event_type,
            e.title = $title,
            e.description = $description,
            e.severity = $severity,
            e.latitude = $latitude,
            e.longitude = $longitude,
            e.region = $region,
            e.resolved_at = datetime()
        WITH e
        MATCH (s:Supplier {name: $supplier_name})
        MERGE (e)-[r:AFFECTS]->(s)
        ON CREATE SET r.confidence = 0.85, r.resolved_at = datetime()
        SET s.risk_score = CASE
            WHEN s.risk_score < $severity THEN $severity
            ELSE s.risk_score
        END
        RETURN e.id AS event_id, s.name AS supplier
        """
        rows = client.execute_query(
            query,
            {
                "id": event["id"],
                "event_type": event["event_type"],
                "title": event["title"],
                "description": event["description"],
                "severity": event["severity"],
                "supplier_name": event["supplier_name"],
                "latitude": event["latitude"],
                "longitude": event["longitude"],
                "region": event["region"],
            },
        )
        if rows:
            created += 1
            logger.info("demo_event_linked", event_id=event["id"], supplier=rows[0].get("supplier"))

    print(f"Demo scenarios seeded: {created}/{len(DEMO_EVENTS)} events linked to suppliers")


if __name__ == "__main__":
    main()
