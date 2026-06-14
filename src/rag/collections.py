"""Qdrant collection helpers — events, suppliers, methodology."""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from .embedder import get_embedder
from .qdrant_client import get_qdrant_store

logger = structlog.get_logger(__name__)


class RagCollection(str, Enum):
    EVENTS = "meridian_events"
    SUPPLIERS = "meridian_suppliers"
    METHODOLOGY = "meridian_methodology"


def _stable_id(collection: RagCollection, key: str) -> int:
    """Map string keys to positive int IDs for Qdrant."""
    digest = hashlib.sha256(f"{collection.value}:{key}".encode()).hexdigest()
    return int(digest[:15], 16)


def upsert_documents(
    collection: RagCollection,
    documents: List[Dict[str, Any]],
) -> int:
    """Upsert documents with ``id``, ``text``, and optional ``metadata``."""
    if not documents:
        return 0
    embedder = get_embedder()
    store = get_qdrant_store()
    texts = [d["text"] for d in documents]
    vectors = embedder.embed_batch(texts)
    points = []
    for doc, vector in zip(documents, vectors):
        doc_id = doc.get("id") or doc.get("key", doc["text"][:64])
        payload = {
            "text": doc["text"],
            "source": doc.get("source", collection.value),
            **(doc.get("metadata") or {}),
        }
        points.append(
            {
                "id": _stable_id(collection, str(doc_id)),
                "vector": vector,
                "payload": payload,
            }
        )
    count = store.upsert(collection.value, points, embedder.vector_size)
    logger.info("rag_upsert_complete", collection=collection.value, count=count)
    return count


def search_collection(
    collection: RagCollection,
    query: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Semantic search within a single collection."""
    embedder = get_embedder()
    store = get_qdrant_store()
    if not store.is_available:
        return []
    vector = embedder.embed(query)
    hits = store.search(collection.value, vector, limit=limit)
    return [
        {
            "collection": collection.value,
            "score": hit["score"],
            "text": (hit["payload"] or {}).get("text", ""),
            "source": (hit["payload"] or {}).get("source", collection.value),
            "metadata": {
                k: v
                for k, v in (hit["payload"] or {}).items()
                if k not in ("text", "source")
            },
        }
        for hit in hits
    ]


def search_all(query: str, limit_per_collection: int = 3) -> List[Dict[str, Any]]:
    """Search events, suppliers, and methodology collections."""
    results: List[Dict[str, Any]] = []
    for collection in RagCollection:
        results.extend(search_collection(collection, query, limit=limit_per_collection))
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return results
