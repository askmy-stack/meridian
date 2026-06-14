"""Qdrant vector store client — graceful skip when service is down."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None  # type: ignore[misc, assignment]
    qmodels = None  # type: ignore[misc, assignment]


class QdrantStore:
    """Thin wrapper around Qdrant with availability probing."""

    def __init__(self, url: Optional[str] = None) -> None:
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self._client: Optional[Any] = None
        self._available: Optional[bool] = None
        self.logger = logger.bind(component="QdrantStore", url=self.url)

    @property
    def is_available(self) -> bool:
        """Return True when Qdrant responds to a health check."""
        if not QDRANT_AVAILABLE:
            return False
        if self._available is not None:
            return self._available
        try:
            client = self._get_client()
            client.get_collections()
            self._available = True
        except Exception as exc:
            self.logger.info("qdrant_unavailable", error=str(exc))
            self._available = False
        return self._available

    def _get_client(self) -> Any:
        if not QDRANT_AVAILABLE:
            raise RuntimeError("qdrant-client not installed")
        if self._client is None:
            self._client = QdrantClient(url=self.url, timeout=5)
        return self._client

    def ensure_collection(self, name: str, vector_size: int) -> bool:
        """Create collection if missing. Returns False when Qdrant is down."""
        if not self.is_available:
            return False
        try:
            client = self._get_client()
            existing = {c.name for c in client.get_collections().collections}
            if name not in existing:
                client.create_collection(
                    collection_name=name,
                    vectors_config=qmodels.VectorParams(
                        size=vector_size,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                self.logger.info("qdrant_collection_created", collection=name)
            return True
        except Exception as exc:
            self.logger.warning("qdrant_ensure_collection_failed", collection=name, error=str(exc))
            self._available = False
            return False

    def upsert(
        self,
        collection: str,
        points: List[Dict[str, Any]],
        vector_size: int,
    ) -> int:
        """Upsert points with ``id``, ``vector``, and ``payload`` keys."""
        if not points:
            return 0
        if not self.ensure_collection(collection, vector_size):
            return 0
        try:
            qpoints = [
                qmodels.PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ]
            self._get_client().upsert(collection_name=collection, points=qpoints)
            return len(qpoints)
        except Exception as exc:
            self.logger.warning("qdrant_upsert_failed", collection=collection, error=str(exc))
            return 0

    def search(
        self,
        collection: str,
        vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search collection; returns empty list when unavailable."""
        if not self.is_available:
            return []
        try:
            hits = self._get_client().search(
                collection_name=collection,
                query_vector=vector,
                limit=limit,
                score_threshold=score_threshold,
            )
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload or {},
                }
                for hit in hits
            ]
        except Exception as exc:
            self.logger.warning("qdrant_search_failed", collection=collection, error=str(exc))
            return []


_store: Optional[QdrantStore] = None


def get_qdrant_store() -> QdrantStore:
    """Singleton Qdrant store."""
    global _store
    if _store is None:
        _store = QdrantStore()
    return _store
