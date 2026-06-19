"""Kafka consumer — stream normalized events into Qdrant RAG index."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import structlog
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from ..rag.collections import RagCollection, upsert_documents
from ..rag.indexing import event_kafka_to_rag_doc
from ..rag.qdrant_client import get_qdrant_store
from .pipeline_topics import GRAPH_LOADER_TOPICS

logger = structlog.get_logger(__name__)

DEFAULT_TOPICS = GRAPH_LOADER_TOPICS


class RagIndexerConsumer:
    """Embed and upsert Kafka conflict events into meridian_events collection."""

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        group_id: str = "meridian-rag-indexer",
        topics: Optional[List[str]] = None,
        auto_offset_reset: str = "earliest",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.group_id = group_id
        self.topics = topics or DEFAULT_TOPICS
        self.auto_offset_reset = auto_offset_reset
        self.logger = logger.bind(consumer="RagIndexerConsumer", group_id=group_id)
        self._consumer: Optional[KafkaConsumer] = None
        self.stats = {"messages": 0, "indexed": 0, "skipped": 0, "errors": 0}

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

    def index_event(self, event: Dict[str, Any]) -> bool:
        """Embed and upsert a single Kafka event."""
        store = get_qdrant_store()
        if not store.is_available:
            self.stats["skipped"] += 1
            return False

        doc = event_kafka_to_rag_doc(event)
        if not doc:
            self.stats["skipped"] += 1
            return False

        try:
            count = upsert_documents(RagCollection.EVENTS, [doc])
            if count:
                self.stats["indexed"] += 1
                self.logger.info(
                    "rag_index_event",
                    event_id=event.get("event_id"),
                    region=doc.get("metadata", {}).get("region"),
                )
                return True
        except Exception as exc:
            self.logger.warning("rag_index_event_failed", error=str(exc))
            self.stats["errors"] += 1
        return False

    def run(self, max_messages: Optional[int] = None) -> Dict[str, int]:
        """Poll Kafka and index events until idle or max_messages reached."""
        self.connect()
        assert self._consumer is not None

        idle_rounds = 0
        max_idle = int(os.getenv("RAG_INDEXER_MAX_IDLE_ROUNDS", "3"))

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
                        self.index_event(payload)

                    if max_messages and self.stats["messages"] >= max_messages:
                        break

        self.close()
        return self.stats.copy()

    def close(self) -> None:
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        self.logger.info("rag_indexer_closed", stats=self.stats)
