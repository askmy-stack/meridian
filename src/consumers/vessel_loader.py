"""Vessel loader consumer — persists AISHub events into Neo4j."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import structlog
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ..graph import get_neo4j_client
from .pipeline_topics import VESSEL_LOADER_TOPICS

logger = structlog.get_logger(__name__)


def vessel_event_to_props(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a Kafka VesselEvent payload to Neo4j upsert properties."""
    mmsi = event.get("mmsi")
    location = event.get("location") or {}
    lat = location.get("latitude")
    lon = location.get("longitude")

    if not mmsi or lat is None or lon is None:
        return None

    raw = event.get("raw_data") or {}
    chokepoint = raw.get("in_chokepoint")

    return {
        "mmsi": str(mmsi),
        "vessel_name": event.get("vessel_name") or f"Vessel {mmsi}",
        "vessel_type": event.get("vessel_type"),
        "latitude": float(lat),
        "longitude": float(lon),
        "speed": float(event["speed"]) if event.get("speed") is not None else None,
        "heading": float(event["heading"]) if event.get("heading") is not None else None,
        "event_type": event.get("event_type", "position"),
        "event_id": event.get("event_id"),
        "chokepoint_name": chokepoint,
        "destination_port": event.get("destination_port"),
    }


class VesselLoaderConsumer:
    """Consume AIS vessel events and upsert Vessel nodes + chokepoint links."""

    UPSERT_VESSEL = """
    MERGE (v:Vessel {mmsi: $mmsi})
    SET v.name = $vessel_name,
        v.vessel_type = $vessel_type,
        v.latitude = $latitude,
        v.longitude = $longitude,
        v.speed = $speed,
        v.heading = $heading,
        v.last_seen = datetime(),
        v.source = 'aishub'
    RETURN v.mmsi AS mmsi
    """

    LINK_CHOKEPOINT = """
    MATCH (v:Vessel {mmsi: $mmsi})
    MATCH (c:Chokepoint {name: $chokepoint_name})
    MERGE (v)-[r:TRANSITING]->(c)
    SET r.observed_at = datetime(),
        r.event_id = $event_id,
        r.speed = $speed
    RETURN v.mmsi AS mmsi, c.name AS chokepoint
    """

    UPDATE_CONGESTION = """
    MATCH (c:Chokepoint {name: $chokepoint_name})
    SET c.vessel_count = coalesce(c.vessel_count, 0) + 1,
        c.last_ais_update = datetime()
    RETURN c.name AS name
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        group_id: str = "meridian-vessel-loader",
        topics: Optional[List[str]] = None,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.group_id = group_id
        self.topics = topics or VESSEL_LOADER_TOPICS
        self.auto_offset_reset = auto_offset_reset
        self.logger = logger.bind(consumer="VesselLoaderConsumer", group_id=group_id)
        self._consumer: Optional[KafkaConsumer] = None
        self.neo4j = get_neo4j_client()
        self.stats = {"messages": 0, "loaded": 0, "linked": 0, "skipped": 0, "errors": 0}

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

    def load_event(self, event: Dict[str, Any]) -> bool:
        """Upsert vessel and optionally link to chokepoint."""
        props = vessel_event_to_props(event)
        if not props:
            self.stats["skipped"] += 1
            return False

        try:
            rows = self.neo4j.execute_query(self.UPSERT_VESSEL, props)
            if not rows:
                self.stats["skipped"] += 1
                return False

            self.stats["loaded"] += 1

            if props.get("chokepoint_name"):
                self.neo4j.execute_query(self.LINK_CHOKEPOINT, props)
                self.neo4j.execute_query(
                    self.UPDATE_CONGESTION,
                    {"chokepoint_name": props["chokepoint_name"]},
                )
                self.stats["linked"] += 1
            return True
        except Exception as exc:
            self.logger.error(
                "vessel_load_failed",
                mmsi=props.get("mmsi"),
                error=str(exc),
            )
            self.stats["errors"] += 1
        return False

    def run(self, max_messages: Optional[int] = None) -> Dict[str, int]:
        """Poll Kafka and load vessel events until idle or max_messages reached."""
        self.connect()
        assert self._consumer is not None

        idle_rounds = 0
        max_idle = int(os.getenv("VESSEL_LOADER_MAX_IDLE_ROUNDS", "3"))

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
                        payload = {
                            k: v for k, v in payload.items() if k != "_meridian_metadata"
                        }
                        self.load_event(payload)

                    if max_messages and self.stats["messages"] >= max_messages:
                        break

        self.close()
        return self.stats.copy()

    def close(self) -> None:
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        self.logger.info("vessel_loader_closed", stats=self.stats)
