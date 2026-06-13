#!/usr/bin/env python3
"""Scheduled ingestion job: GDELT + ACLED + AIS → Kafka → Neo4j → alerts.

Run manually or via cron:
    python scripts/pipeline_refresh.py

Requires: docker compose up -d kafka neo4j (and seeded suppliers for entity links).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)


def _emit_high_severity_alerts(min_severity: float = 0.75) -> int:
    """Emit Slack-ready alerts for newly ingested high-severity events."""
    from src.alerting import get_alerting_service
    from src.alerting.slack import Alert, AlertTier
    from src.graph import get_neo4j_client

    client = get_neo4j_client()
    rows = client.execute_query(
        """
        MATCH (e:Event)
        WHERE e.severity >= $min_severity
          AND e.ingested_at > datetime() - duration('PT1H')
        RETURN e.id AS id, e.title AS title, e.description AS description,
               e.severity AS severity, e.region AS region
        ORDER BY e.severity DESC
        LIMIT 10
        """,
        {"min_severity": min_severity},
    )

    service = get_alerting_service()
    sent = 0
    for row in rows:
        tier = AlertTier.CRITICAL if row["severity"] >= 0.85 else AlertTier.WARNING
        alert = Alert(
            tier=tier,
            title=f"Signal: {row['title']}",
            message=row.get("description") or f"Elevated risk in {row.get('region', 'region')}",
            entity_id=row["id"],
            entity_type="event",
            risk_score=float(row["severity"]),
            recommendations=[
                "Review affected suppliers on the risk map",
                "Run a disruption scenario for this region",
            ],
        )
        if service.send_alert(alert):
            sent += 1

    return sent


def _publish_gdelt(bootstrap: str) -> int:
    from src.producers.gdelt_producer import GDELTProducer

    producer = GDELTProducer(bootstrap_servers=bootstrap)
    published = producer.fetch_and_publish(hours_back=1)
    producer.disconnect()
    logger.info("gdelt_published", count=published)
    print(f"GDELT published: {published} events")
    return published


def _publish_acled(bootstrap: str) -> int:
    if not os.getenv("ACLED_API_KEY") or not os.getenv("ACLED_EMAIL"):
        print("ACLED skipped — set ACLED_API_KEY and ACLED_EMAIL in .env")
        return 0

    from src.producers.acled_producer import ACLEDProducer

    producer = ACLEDProducer(bootstrap_servers=bootstrap)
    published = producer.fetch_and_publish(days_back=1)
    producer.disconnect()
    logger.info("acled_published", count=published)
    print(f"ACLED published: {published} events")
    return published


def _publish_ais(bootstrap: str) -> int:
    if not os.getenv("AISHUB_USERNAME"):
        print("AIS skipped — set AISHUB_USERNAME (and AISHUB_PASSWORD) in .env")
        return 0

    from src.producers.ais_producer import AISProducer

    producer = AISProducer(bootstrap_servers=bootstrap)
    published = producer.fetch_and_publish(filter_chokepoints=True)
    producer.disconnect()
    logger.info("ais_published", count=published)
    print(f"AIS published: {published} vessel events")
    return published


def main() -> int:
    load_dotenv()
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    max_messages = int(os.getenv("PIPELINE_MAX_MESSAGES", "500"))

    from src.consumers.entity_resolution import EntityResolutionConsumer
    from src.consumers.graph_loader import GraphLoaderConsumer
    from src.consumers.pipeline_topics import ENTITY_RESOLUTION_TOPICS
    from src.consumers.vessel_loader import VesselLoaderConsumer

    logger.info("pipeline_refresh_started", bootstrap=bootstrap)

    publish_counts: Dict[str, int] = {
        "gdelt": _publish_gdelt(bootstrap),
        "acled": _publish_acled(bootstrap),
        "ais": _publish_ais(bootstrap),
    }
    total_published = sum(publish_counts.values())

    if total_published == 0:
        print("No events published from any source — skipping consumer stages")
        return 0

    loader = GraphLoaderConsumer(bootstrap_servers=bootstrap)
    load_stats = loader.run(max_messages=max_messages)
    print(f"Graph loader: {load_stats}")

    vessel_stats = {"loaded": 0, "linked": 0}
    if publish_counts["ais"] > 0:
        vessel_loader = VesselLoaderConsumer(bootstrap_servers=bootstrap)
        vessel_stats = vessel_loader.run(max_messages=max_messages)
        print(f"Vessel loader: {vessel_stats}")

    resolver = EntityResolutionConsumer(bootstrap_servers=bootstrap)
    resolver.subscribe(ENTITY_RESOLUTION_TOPICS)
    resolver.run(max_messages=max_messages)
    print(f"Entity resolution: {resolver.get_stats()}")

    alerts_sent = _emit_high_severity_alerts()
    print(f"Alerts emitted: {alerts_sent}")

    logger.info(
        "pipeline_refresh_complete",
        published=publish_counts,
        loaded=load_stats.get("loaded", 0),
        vessels=vessel_stats.get("loaded", 0),
        alerts=alerts_sent,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
