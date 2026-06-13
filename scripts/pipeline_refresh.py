#!/usr/bin/env python3
"""Scheduled ingestion job: GDELT → Kafka → Neo4j → alerts.

Run manually or via cron:
    python scripts/pipeline_refresh.py

Requires: docker compose up -d kafka neo4j (and seeded suppliers for entity links).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

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


def main() -> int:
    load_dotenv()
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    max_messages = int(os.getenv("PIPELINE_MAX_MESSAGES", "500"))

    from src.producers.gdelt_producer import GDELTProducer
    from src.consumers.graph_loader import GraphLoaderConsumer
    from src.consumers.entity_resolution import EntityResolutionConsumer

    logger.info("pipeline_refresh_started", bootstrap=bootstrap)

    # 1) Publish latest GDELT slice to Kafka
    producer = GDELTProducer(bootstrap_servers=bootstrap)
    published = producer.fetch_and_publish(hours_back=1)
    producer.disconnect()
    logger.info("gdelt_published", count=published)
    print(f"GDELT published: {published} events")

    if published == 0:
        print("No new GDELT rows — skipping consumer stages")
        return 0

    # 2) Load Kafka events into Neo4j
    loader = GraphLoaderConsumer(bootstrap_servers=bootstrap)
    load_stats = loader.run(max_messages=max_messages)
    print(f"Graph loader: {load_stats}")

    # 3) Link events to suppliers / chokepoints
    resolver = EntityResolutionConsumer(bootstrap_servers=bootstrap)
    resolver.subscribe(
        [
            "meridian.gdelt.conflict",
            "meridian.gdelt.protest",
            "meridian.gdelt.fight",
            "meridian.gdelt.assault",
        ]
    )
    resolver.run(max_messages=max_messages)
    print(f"Entity resolution: {resolver.get_stats()}")

    # 4) Alert on high-severity ingested events
    alerts_sent = _emit_high_severity_alerts()
    print(f"Alerts emitted: {alerts_sent}")

    logger.info(
        "pipeline_refresh_complete",
        published=published,
        loaded=load_stats.get("loaded", 0),
        alerts=alerts_sent,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
