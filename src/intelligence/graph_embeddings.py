"""Supplier graph embeddings for alternative-supplier recommendations."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 32


@dataclass
class SupplierEmbedding:
    """Lightweight embedding vector for a supplier node."""

    supplier_id: str
    name: str
    vector: List[float]
    risk_score: float
    industry: Optional[str] = None
    country_iso: Optional[str] = None


def _hash_walk_embedding(
    supplier_id: str,
    neighbors: List[str],
    risk_score: float,
    dim: int = EMBEDDING_DIM,
) -> List[float]:
    """Deterministic random-walk-style stub embedding (no Node2Vec dependency)."""
    seed = int(hashlib.sha256(supplier_id.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    base = rng.normal(0, 1, size=dim)
    for i, nid in enumerate(neighbors[:8]):
        nseed = int(hashlib.sha256(nid.encode()).hexdigest()[:8], 16)
        nvec = np.random.default_rng(nseed).normal(0, 0.3, size=dim)
        base += nvec / (i + 2)
    base += np.array([risk_score] * dim) * 0.15
    norm = np.linalg.norm(base)
    if norm > 0:
        base = base / norm
    return base.tolist()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _fetch_supplier_subgraph(limit: int = 200) -> List[Dict[str, Any]]:
    """Load supplier nodes and SUPPLIES neighbors from Neo4j."""
    try:
        from ..graph import get_neo4j_client

        client = get_neo4j_client()
        rows = client.execute_query(
            """
            MATCH (s:Supplier)
            OPTIONAL MATCH (s)-[:SUPPLIES|SHIPS_VIA]-(n)
            WHERE n:Supplier OR n:Port
            WITH s, collect(DISTINCT coalesce(n.id, n.name)) AS neighbors
            RETURN s.id AS id, s.name AS name, s.risk_score AS risk_score,
                   s.industry AS industry, s.country_iso AS country_iso,
                   neighbors
            LIMIT $limit
            """,
            {"limit": limit},
        )
        return rows
    except Exception as exc:
        logger.warning("embedding_subgraph_failed", error=str(exc))
        return []


def build_supplier_embeddings(limit: int = 200) -> Dict[str, SupplierEmbedding]:
    """Build embedding index for suppliers (Node2Vec stub via random-walk hash)."""
    rows = _fetch_supplier_subgraph(limit=limit)
    embeddings: Dict[str, SupplierEmbedding] = {}
    for row in rows:
        sid = row.get("id")
        if not sid:
            continue
        risk = float(row.get("risk_score") or 0.5)
        neighbors = [n for n in (row.get("neighbors") or []) if n]
        vec = _hash_walk_embedding(sid, neighbors, risk)
        embeddings[sid] = SupplierEmbedding(
            supplier_id=sid,
            name=row.get("name") or sid,
            vector=vec,
            risk_score=risk,
            industry=row.get("industry"),
            country_iso=row.get("country_iso"),
        )
    return embeddings


def rank_alternative_suppliers(
    supplier_id: str,
    *,
    limit: int = 5,
    embeddings: Optional[Dict[str, SupplierEmbedding]] = None,
) -> List[Dict[str, Any]]:
    """Rank alternative suppliers by embedding similarity and inverse risk."""
    index = embeddings if embeddings is not None else build_supplier_embeddings()
    target = index.get(supplier_id)
    if not target:
        return []

    candidates: List[Tuple[float, SupplierEmbedding]] = []
    for sid, emb in index.items():
        if sid == supplier_id:
            continue
        sim = cosine_similarity(target.vector, emb.vector)
        inverse_risk = 1.0 - emb.risk_score
        score = 0.6 * sim + 0.4 * inverse_risk
        candidates.append((score, emb))

    candidates.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, emb in candidates[:limit]:
        results.append({
            "supplier_id": emb.supplier_id,
            "name": emb.name,
            "country_iso": emb.country_iso,
            "industry": emb.industry,
            "risk_score": round(emb.risk_score, 4),
            "similarity": round(cosine_similarity(target.vector, emb.vector), 4),
            "rank_score": round(score, 4),
            "method": "node2vec_stub",
        })
    return results
