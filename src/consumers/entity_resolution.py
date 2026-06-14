"""Entity Resolution Consumer for Meridian.

Reads conflict/news events from Kafka, extracts entity mentions,
and links them to graph entities (suppliers, ports, chokepoints).

Architecture:
    meridian.news.events (Kafka) 
        -> EntityResolutionConsumer
            -> NER extraction (SimpleNERExtractor)
            -> Fuzzy matching (FuzzyEntityMatcher)
            -> Graph relationship creation (Neo4j)
"""

import json
import os
from typing import Any, Dict, List, Optional

import structlog
from kafka import KafkaConsumer, TopicPartition
from kafka.errors import KafkaError

from ..entity_resolution.fuzzy_matcher import (
    FuzzyEntityMatcher,
    SimpleNERExtractor,
    get_fuzzy_matcher,
    get_ner_extractor,
)
from ..graph import get_neo4j_client, get_supplier_repository

logger = structlog.get_logger(__name__)


class EntityResolutionConsumer:
    """Kafka consumer for entity resolution from news/conflict events.
    
    Consumes from `meridian.news.events` or similar topic, extracts
    entity mentions from event descriptions, and creates relationships
    between events and affected supply chain entities in Neo4j.
    
    Usage:
        consumer = EntityResolutionConsumer(bootstrap_servers="localhost:9092")
        consumer.subscribe(["meridian.gdelt.conflict"])
        consumer.run()  # Blocking, runs indefinitely
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "meridian-entity-resolution",
        auto_offset_reset: str = "earliest",
        fuzzy_threshold: int = 70,
        enable_auto_commit: bool = True
    ):
        """Initialize entity resolution consumer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            group_id: Consumer group ID
            auto_offset_reset: Where to start if no committed offset
            fuzzy_threshold: Minimum score (0-100) for fuzzy matching
            enable_auto_commit: Auto-commit offsets to Kafka
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.fuzzy_threshold = fuzzy_threshold
        self.enable_auto_commit = enable_auto_commit
        
        self.logger = logger.bind(
            consumer="EntityResolutionConsumer",
            group_id=group_id
        )
        
        # Entity resolution components
        self.ner_extractor = get_ner_extractor()
        self.fuzzy_matcher = get_fuzzy_matcher()
        self.fuzzy_matcher.threshold = fuzzy_threshold
        
        # Neo4j
        self.neo4j_client = get_neo4j_client()
        self.supplier_repo = get_supplier_repository()
        
        # Kafka consumer (initialized in connect())
        self._consumer: Optional[KafkaConsumer] = None
        
        # Processing statistics
        self.stats = {
            "events_processed": 0,
            "entities_linked": 0,
            "suppliers_linked": 0,
            "ports_linked": 0,
            "chokepoints_linked": 0,
            "errors": 0
        }
    
    def connect(self) -> None:
        """Initialize Kafka consumer connection."""
        try:
            self._consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=self.enable_auto_commit,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda m: m.decode("utf-8") if m else None,
                consumer_timeout_ms=1000  # 1 second timeout for polling
            )
            
            self.logger.info(
                "kafka_consumer_connected",
                bootstrap_servers=self.bootstrap_servers
            )
            
        except KafkaError as e:
            self.logger.error("kafka_connection_failed", error=str(e))
            raise
    
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to Kafka topics.
        
        Args:
            topics: List of topic names to subscribe to
        """
        if self._consumer is None:
            self.connect()
        
        self._consumer.subscribe(topics)
        self.logger.info("subscribed_to_topics", topics=topics)
    
    def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single event: extract entities and link to graph.
        
        Args:
            event: Parsed Kafka message value
            
        Returns:
            Processing result with linked entities
        """
        result = {
            "event_id": event.get("event_id", "unknown"),
            "suppliers_linked": [],
            "ports_linked": [],
            "chokepoints_linked": [],
            "extracted_mentions": []
        }
        
        try:
            # Get text to analyze
            text = self._extract_text_from_event(event)
            
            if not text:
                self.logger.debug("no_text_in_event", event_id=result["event_id"])
                return result
            
            # Extract entity mentions
            supplier_mentions = self.ner_extractor.extract_supplier_mentions(text)
            port_mentions = self.ner_extractor.extract_port_mentions(text)
            chokepoint_mentions = self.ner_extractor.extract_chokepoint_mentions(text)
            
            result["extracted_mentions"] = {
                "suppliers": supplier_mentions,
                "ports": port_mentions,
                "chokepoints": chokepoint_mentions
            }
            
            # Link suppliers using fuzzy matching
            for mention in supplier_mentions:
                match = self.fuzzy_matcher.match_supplier(
                    mention,
                    threshold=self.fuzzy_threshold
                )
                
                if match:
                    supplier, score = match
                    
                    # Create relationship: Event -[AFFECTS]-> Supplier
                    self._link_event_to_supplier(result["event_id"], supplier.id, score)
                    
                    result["suppliers_linked"].append({
                        "supplier_id": supplier.id,
                        "name": supplier.name,
                        "match_score": score,
                        "mention": mention
                    })
                    
                    self.stats["suppliers_linked"] += 1
                    self.stats["entities_linked"] += 1
            
            # Link chokepoints (exact matching since we have canonical names)
            for mention in chokepoint_mentions:
                self._link_event_to_chokepoint(result["event_id"], mention)
                result["chokepoints_linked"].append({"name": mention})
                self.stats["chokepoints_linked"] += 1
                self.stats["entities_linked"] += 1
            
            self.stats["events_processed"] += 1
            
            self.logger.info(
                "event_processed",
                event_id=result["event_id"],
                suppliers_linked=len(result["suppliers_linked"]),
                chokepoints_linked=len(result["chokepoints_linked"])
            )
            
        except Exception as e:
            self.logger.error(
                "event_processing_failed",
                event_id=result["event_id"],
                error=str(e)
            )
            self.stats["errors"] += 1
            result["error"] = str(e)
        
        return result
    
    def _extract_text_from_event(self, event: Dict[str, Any]) -> str:
        """Extract searchable text from event payload.
        
        Tries multiple fields in order of relevance:
        1. description (GDELT, ACLED)
        2. notes (ACLED)
        3. headline/news_title
        4. raw_data as fallback
        """
        # Try explicit text fields
        for field in ["description", "notes", "headline", "news_title", "title"]:
            if field in event and event[field]:
                return str(event[field])
        
        # Try nested in raw_data
        if "raw_data" in event and isinstance(event["raw_data"], dict):
            raw = event["raw_data"]
            for field in ["description", "notes", "title", "source_url"]:
                if field in raw and raw[field]:
                    return str(raw[field])
        
        return ""
    
    def _link_event_to_supplier(
        self,
        event_id: str,
        supplier_id: str,
        confidence: float
    ) -> bool:
        """Create AFFECTS relationship between event and supplier.
        
        Args:
            event_id: Event ID (e.g., "gdelt_123456")
            supplier_id: Supplier UUID
            confidence: Match confidence score (0-100)
            
        Returns:
            True if relationship created
        """
        query = """
        MERGE (e:Event {id: $event_id})
        ON CREATE SET e.resolved_at = datetime()
        
        WITH e
        MATCH (s:Supplier {id: $supplier_id})
        
        MERGE (e)-[r:AFFECTS]->(s)
        ON CREATE SET
            r.link_method = 'manual',
            r.confidence = $confidence,
            r.linked_at = datetime()
        ON MATCH SET
            r.link_method = coalesce(r.link_method, 'manual'),
            r.confidence = CASE
                WHEN r.confidence IS NULL OR $confidence > r.confidence THEN $confidence
                ELSE r.confidence
            END,
            r.linked_at = coalesce(r.linked_at, datetime())
        
        RETURN count(r) as created
        """
        
        try:
            with self.neo4j_client.session() as session:
                result = session.run(query, {
                    "event_id": event_id,
                    "supplier_id": supplier_id,
                    "confidence": confidence / 100.0  # Normalize to 0-1
                })
                record = result.single()
                return record["created"] > 0 if record else False
        except Exception as e:
            self.logger.error(
                "link_creation_failed",
                event_id=event_id,
                supplier_id=supplier_id,
                error=str(e)
            )
            return False
    
    def _link_event_to_chokepoint(self, event_id: str, chokepoint_name: str) -> bool:
        """Create AFFECTS relationship between event and chokepoint."""
        query = """
        MERGE (e:Event {id: $event_id})
        ON CREATE SET e.resolved_at = datetime()
        
        WITH e
        MATCH (c:Chokepoint)
        WHERE toLower(c.name) CONTAINS toLower($chokepoint_name)
        
        MERGE (e)-[r:AFFECTS]->(c)
        ON CREATE SET r.resolved_at = datetime()
        
        RETURN count(r) as created
        """
        
        try:
            with self.neo4j_client.session() as session:
                result = session.run(query, {
                    "event_id": event_id,
                    "chokepoint_name": chokepoint_name
                })
                record = result.single()
                return record["created"] > 0 if record else False
        except Exception as e:
            self.logger.error(
                "chokepoint_link_failed",
                event_id=event_id,
                chokepoint=chokepoint_name,
                error=str(e)
            )
            return False
    
    def run(self, max_messages: Optional[int] = None) -> None:
        """Run consumer loop.
        
        Args:
            max_messages: Process N messages then stop (None = infinite)
        """
        if self._consumer is None:
            raise RuntimeError("Not subscribed to any topics. Call subscribe() first.")
        
        self.logger.info(
            "consumer_started",
            max_messages=max_messages,
            fuzzy_threshold=self.fuzzy_threshold
        )
        
        message_count = 0
        
        try:
            while max_messages is None or message_count < max_messages:
                # Poll for messages
                records = self._consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in records.items():
                    for message in messages:
                        event = message.value
                        
                        self.logger.debug(
                            "message_received",
                            topic=topic_partition.topic,
                            partition=topic_partition.partition,
                            offset=message.offset
                        )
                        
                        # Process the event
                        self.process_event(event)
                        
                        message_count += 1
                        
                        if max_messages and message_count >= max_messages:
                            break
                    
                    if max_messages and message_count >= max_messages:
                        break
        
        except KeyboardInterrupt:
            self.logger.info("consumer_stopped_by_user")
        except Exception as e:
            self.logger.error("consumer_error", error=str(e))
            raise
        finally:
            self.close()
    
    def close(self) -> None:
        """Close consumer and connections."""
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        
        self.neo4j_client.close()
        
        self.logger.info(
            "consumer_closed",
            stats=self.stats
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.stats.copy()


if __name__ == "__main__":
    import sys
    
    # CLI usage
    consumer = EntityResolutionConsumer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        fuzzy_threshold=int(os.getenv("FUZZY_THRESHOLD", "70"))
    )
    
    # Subscribe to conflict and protest events
    consumer.subscribe([
        "meridian.gdelt.conflict",
        "meridian.gdelt.protest",
        "meridian.acled.conflict"
    ])
    
    # Run (Ctrl+C to stop)
    print("Starting entity resolution consumer...")
    print("Topics: meridian.gdelt.conflict, meridian.gdelt.protest, meridian.acled.conflict")
    print("Press Ctrl+C to stop")
    
    try:
        consumer.run()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        print(f"Stats: {consumer.get_stats()}")
        sys.exit(0)
