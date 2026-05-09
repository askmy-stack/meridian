"""Base Kafka producer with common functionality."""
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from kafka import KafkaProducer
from kafka.errors import KafkaError
from pydantic import BaseModel

logger = structlog.get_logger()


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class BaseProducer(ABC):
    """Base class for all Meridian data producers.
    
    Provides:
    - Kafka connection management
    - Structured logging
    - JSON serialization with datetime handling
    - Topic naming convention: meridian.{source}.{event_type}
    """
    
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        source_name: str = "unknown",
        max_retries: int = 3
    ):
        self.source_name = source_name
        self.max_retries = max_retries
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        
        self._producer: Optional[KafkaProducer] = None
        self._connected = False
        
        self.logger = logger.bind(
            producer=self.__class__.__name__,
            source=source_name,
            bootstrap_servers=self.bootstrap_servers
        )
    
    def connect(self) -> None:
        """Initialize Kafka connection."""
        if self._connected:
            return
            
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(
                    v, cls=DateTimeEncoder
                ).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=self.max_retries,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                compression_type='gzip'
            )
            self._connected = True
            self.logger.info("kafka_connected")
        except KafkaError as e:
            self.logger.error("kafka_connection_failed", error=str(e))
            raise
    
    def disconnect(self) -> None:
        """Close Kafka connection."""
        if self._producer:
            self._producer.close()
            self._connected = False
            self.logger.info("kafka_disconnected")
    
    def _build_topic(self, event_type: str) -> str:
        """Build topic name following convention: meridian.{source}.{event_type}"""
        return f"meridian.{self.source_name}.{event_type}"
    
    def send_event(
        self,
        event: BaseModel,
        event_type: str,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send a Pydantic model to Kafka.
        
        Args:
            event: Pydantic model instance
            event_type: Type of event for topic routing
            key: Optional partition key
            headers: Optional message headers
            
        Returns:
            True if message was sent successfully
        """
        if not self._connected:
            self.connect()
            
        topic = self._build_topic(event_type)
        
        # Convert to dict and add metadata
        message = event.model_dump()
        message['_meridian_metadata'] = {
            'producer': self.__class__.__name__,
            'source': self.source_name,
            'topic': topic,
            'sent_at': datetime.utcnow().isoformat()
        }
        
        # Log before sending
        self.logger.info(
            "sending_event",
            topic=topic,
            event_id=message.get('event_id'),
            event_type=event_type
        )
        
        try:
            future = self._producer.send(
                topic=topic,
                key=key,
                value=message,
                headers=[(k, v.encode()) for k, v in (headers or {}).items()]
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            self.logger.info(
                "event_sent",
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                event_id=message.get('event_id')
            )
            return True
            
        except KafkaError as e:
            self.logger.error(
                "send_failed",
                error=str(e),
                topic=topic,
                event_id=message.get('event_id')
            )
            return False
    
    def flush(self) -> None:
        """Flush all pending messages."""
        if self._producer:
            self._producer.flush()
            self.logger.info("producer_flushed")
    
    @abstractmethod
    def fetch_and_publish(self, **kwargs: Any) -> int:
        """Fetch data from source and publish to Kafka.
        
        Returns:
            Number of events published
        """
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """Check producer health."""
        return {
            "connected": self._connected,
            "source": self.source_name,
            "bootstrap_servers": self.bootstrap_servers
        }
    
    def __enter__(self) -> 'BaseProducer':
        self.connect()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()
