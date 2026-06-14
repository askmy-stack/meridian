"""Graph loader consumer — persists Kafka conflict events into Neo4j.

Pipeline position:
    GDELTProducer → meridian.gdelt.* → GraphLoaderConsumer → Event nodes
    → EntityResolutionConsumer (optional follow-up) → AFFECTS edges
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ..graph import get_neo4j_client
from .pipeline_topics import GRAPH_LOADER_TOPICS

logger = structlog.get_logger(__name__)

DEFAULT_TOPICS = GRAPH_LOADER_TOPICS


def estimate_severity(event: Dict[str, Any]) -> float:
    """Derive 0–1 severity from Goldstein scale or event type."""
    raw = event.get("raw_data") or {}
    goldstein = raw.get("GoldsteinScale") or raw.get("goldstein_scale")
    if goldstein is not None:
        try:
            score = abs(float(goldstein)) / 10.0
            return round(min(max(score, 0.1), 1.0), 3)
        except (TypeError, ValueError):
            pass

    event_type = str(event.get("event_type", "")).lower()
    defaults = {
        "mass_violence": 0.95,
        "fight": 0.85,
        "assault": 0.8,
        "conflict": 0.75,
        "protest": 0.55,
    }
    return defaults.get(event_type, 0.5)


def build_event_title(event: Dict[str, Any]) -> str:
    """Build a short human-readable title for map/timeline UI."""
    actors = event.get("actors") or []
    region = event.get("region") or event.get("country") or "Unknown region"
    event_type = str(event.get("event_type", "event")).replace("_", " ")
    if actors:
        return f"{event_type.title()} — {actors[0]} ({region})"
    return f"{event_type.title()} in {region}"


def kafka_event_to_graph_props(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a Kafka ConflictEvent payload to Neo4j Event properties."""
    event_id = event.get("event_id")
    location = event.get("location") or {}
    lat = location.get("latitude")
    lon = location.get("longitude")

    if not event_id or lat is None or lon is None:
        return None

    description = event.get("description") or event.get("notes") or "Geopolitical signal"
    return {
        "id": event_id,
        "event_type": event.get("event_type", "conflict"),
        "title": build_event_title(event),
        "description": description[:500],
        "severity": estimate_severity(event),
        "latitude": float(lat),
        "longitude": float(lon),
        "region": event.get("region") or event.get("country") or "Unknown",
        "source": event.get("source", "kafka"),
        "country": event.get("country"),
    }


class GraphLoaderConsumer:
    """Consume conflict events from Kafka and upsert Event nodes in Neo4j."""

    UPSERT_QUERY = """
    MERGE (e:Event {id: $id})
    SET e.event_type = $event_type,
        e.title = $title,
        e.description = $description,
        e.severity = $severity,
        e.latitude = $latitude,
        e.longitude = $longitude,
        e.region = $region,
        e.source = $source,
        e.country = $country,
        e.resolved_at = datetime(),
        e.ingested_at = datetime()
    RETURN e.id AS id
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        group_id: str = "meridian-graph-loader",
        topics: Optional[List[str]] = None,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.group_id = group_id
        self.topics = topics or DEFAULT_TOPICS
        self.auto_offset_reset = auto_offset_reset
        self.logger = logger.bind(consumer="GraphLoaderConsumer", group_id=group_id)
        self._consumer: Optional[KafkaConsumer] = None
        self.neo4j = get_neo4j_client()
        self.stats = {
            "messages": 0,
            "loaded": 0,
            "skipped": 0,
            "errors": 0,
            "links_created": 0,
        }

    def connect(self) -> None:
        if self._consumer is not None:
            return
        try:
            self._consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                consumer_timeout_ms=1000,
            )
            self.logger.info("kafka_consumer_connected", topics=self.topics)
        except KafkaError as exc:
            self.logger.error("kafka_connection_failed", error=str(exc))
            raise

    def _maybe_classify_event(self, event: Dict[str, Any]) -> None:
        """Optional LLM/rule classifier — structured JSON only, no risk scoring."""
        if os.getenv("ENABLE_LLM_CLASSIFIER", "false").lower() not in ("1", "true", "yes"):
            return
        text = event.get("description") or event.get("notes") or ""
        if len(text) < 10:
            return
        try:
            from ..intelligence.event_classifier import classify_news_event

            result = classify_news_event(text)
            event["classification"] = result.to_dict()
            if result.event_type and not event.get("event_type"):
                event["event_type"] = result.event_type
            self.logger.debug(
                "event_classified",
                event_id=event.get("event_id"),
                event_type=result.event_type,
                classifier=result.classifier,
            )
        except Exception as exc:
            self.logger.warning("event_classification_skipped", error=str(exc))

    def load_event(self, event: Dict[str, Any]) -> bool:
        """Upsert a single Kafka event into Neo4j."""
        self._maybe_classify_event(event)
        props = kafka_event_to_graph_props(event)
        if not props:
            self.stats["skipped"] += 1
            return False

        try:
            rows = self.neo4j.execute_query(self.UPSERT_QUERY, props)
            if rows:
                self.stats["loaded"] += 1
                linked = self._link_event_to_suppliers(props)
                self.stats["links_created"] += linked
                return True
        except Exception as exc:
            self.logger.error("graph_load_failed", event_id=event.get("event_id"), error=str(exc))
            self.stats["errors"] += 1
        return False

    def _link_event_to_suppliers(self, props: Dict[str, Any]) -> int:
        """Link loaded event to suppliers via geospatial + country_match heuristics."""
        from ..graph.affects_links import (
            link_event_to_suppliers_by_country,
            link_event_to_suppliers_by_geospatial,
        )

        event_id = props["id"]
        linked = 0
        try:
            linked += link_event_to_suppliers_by_geospatial(self.neo4j, event_id)
            linked += link_event_to_suppliers_by_country(
                self.neo4j, event_id, props.get("country")
            )
        except Exception as exc:
            self.logger.warning("event_supplier_link_failed", event_id=event_id, error=str(exc))
        return linked

    def _flush_event_signal_history(self) -> None:
        """Persist batch ingest metadata to TimescaleDB when configured."""
        loaded = self.stats.get("loaded", 0)
        if loaded == 0:
            return
        try:
            from ..storage.timescale_writer import EventSignalRecord, get_timescale_writer

            writer = get_timescale_writer()
            writer.write_event_batch_sync(
                [
                    EventSignalRecord(
                        source="graph_loader",
                        linked_supplier_count=int(self.stats.get("links_created", 0)),
                        event_id=None,
                        severity=None,
                    )
                ]
            )
        except Exception as exc:
            self.logger.warning("event_signal_history_skipped", error=str(exc))

    def run(self, max_messages: Optional[int] = None) -> Dict[str, int]:
        """Poll Kafka and load events until idle or max_messages reached."""
        self.connect()
        assert self._consumer is not None

        idle_rounds = 0
        max_idle = int(os.getenv("GRAPH_LOADER_MAX_IDLE_ROUNDS", "3"))

        while max_messages is None or self.stats["messages"] < max_messages:
            records = self._consumer.poll(timeout_ms=1000)
            if not records:
                idle_rounds += 1
                if idle_rounds >= max_idle:
                    break
                continue

            idle_rounds = 0
            for _tp, messages in records.items():
                for message in messages:
                    self.stats["messages"] += 1
                    payload = message.value
                    if isinstance(payload, dict):
                        payload = {k: v for k, v in payload.items() if k != "_meridian_metadata"}
                        self.load_event(payload)

                    if max_messages and self.stats["messages"] >= max_messages:
                        break

        self.close()
        self._flush_event_signal_history()
        return self.stats.copy()

    def close(self) -> None:
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        self.logger.info("graph_loader_closed", stats=self.stats)
