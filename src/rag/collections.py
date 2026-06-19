"""Qdrant collection helpers — events, suppliers, methodology, scenarios, communities."""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

from .embedder import get_embedder
from .qdrant_client import get_qdrant_store

logger = structlog.get_logger(__name__)

METHODOLOGY_KEYWORDS = re.compile(
    r"\b(how\s+calculated|methodology|scri|conformal|shap|xgboost|metrics)\b",
    re.IGNORECASE,
)
BACKTEST_KEYWORDS = re.compile(
    r"\b(suez|ukraine|ever\s+given|backtest|2021|2022|historical)\b",
    re.IGNORECASE,
)
COMMUNITY_KEYWORDS = re.compile(
    r"\b(region|sector|cluster|community|chokepoint|corridor|geography)\b",
    re.IGNORECASE,
)


class RagCollection(str, Enum):
    EVENTS = "meridian_events"
    SUPPLIERS = "meridian_suppliers"
    METHODOLOGY = "meridian_methodology"
    SCENARIOS = "meridian_scenarios"
    BACKTESTS = "meridian_backtests"
    GRAPH_COMMUNITIES = "meridian_graph_communities"


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


def _route_collections(query: str) -> List[Tuple[RagCollection, int]]:
    """Keyword-based collection routing with per-collection limits."""
    defaults: List[Tuple[RagCollection, int]] = [
        (RagCollection.EVENTS, 2),
        (RagCollection.SUPPLIERS, 2),
        (RagCollection.METHODOLOGY, 1),
        (RagCollection.SCENARIOS, 1),
        (RagCollection.BACKTESTS, 1),
        (RagCollection.GRAPH_COMMUNITIES, 1),
    ]
    if METHODOLOGY_KEYWORDS.search(query):
        return [
            (RagCollection.METHODOLOGY, 4),
            (RagCollection.EVENTS, 1),
            (RagCollection.SUPPLIERS, 1),
        ]
    if BACKTEST_KEYWORDS.search(query):
        return [
            (RagCollection.BACKTESTS, 4),
            (RagCollection.SCENARIOS, 2),
            (RagCollection.EVENTS, 1),
        ]
    if COMMUNITY_KEYWORDS.search(query):
        return [
            (RagCollection.GRAPH_COMMUNITIES, 3),
            (RagCollection.SUPPLIERS, 2),
            (RagCollection.EVENTS, 1),
        ]
    return defaults


def search_routed(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search collections with simple keyword routing and score merge."""
    results: List[Dict[str, Any]] = []
    for collection, per_limit in _route_collections(query):
        results.extend(search_collection(collection, query, limit=per_limit))
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return results[:limit]


def search_all(query: str, limit_per_collection: int = 3) -> List[Dict[str, Any]]:
    """Search all collections (flat merge)."""
    results: List[Dict[str, Any]] = []
    for collection in RagCollection:
        results.extend(search_collection(collection, query, limit=limit_per_collection))
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return results
