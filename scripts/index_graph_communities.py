#!/usr/bin/env python3
"""Index supplier graph communities into Qdrant for GraphRAG retrieval."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import structlog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph import get_neo4j_client  # noqa: E402
from src.intelligence.graph_embeddings import _fetch_supplier_subgraph  # noqa: E402
from src.rag.collections import RagCollection, upsert_documents  # noqa: E402
from src.rag.qdrant_client import get_qdrant_store  # noqa: E402

logger = structlog.get_logger(__name__)


def _detect_communities(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Community detection — Louvain when networkx available, else country_iso clusters."""
    try:
        import networkx as nx

        graph = nx.Graph()
        for row in rows:
            sid = row.get("id")
            if not sid:
                continue
            graph.add_node(sid, **row)
            for neighbor in row.get("neighbors") or []:
                if neighbor:
                    graph.add_edge(sid, neighbor)

        try:
            from networkx.algorithms import community as nx_community

            partitions = nx_community.louvain_communities(graph, seed=42)
            communities: Dict[str, List[Dict[str, Any]]] = {}
            for idx, members in enumerate(partitions):
                label = f"community-{idx}"
                communities[label] = [
                    graph.nodes[n] for n in members if n in graph.nodes
                ]
            return communities
        except Exception:
            pass
    except ImportError:
        pass

    by_country: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        country = row.get("country_iso") or "unknown"
        by_country[country].append(row)
    return {f"region-{k}": v for k, v in by_country.items()}


def _community_summary(community_id: str, members: List[Dict[str, Any]]) -> str:
    """Deterministic community summary (no external LLM required)."""
    risks = [float(m.get("risk_score") or 0) for m in members]
    avg_risk = sum(risks) / len(risks) if risks else 0.0
    countries = sorted({m.get("country_iso") for m in members if m.get("country_iso")})
    industries = sorted({m.get("industry") for m in members if m.get("industry")})
    names = [m.get("name") for m in members[:5] if m.get("name")]
    return (
        f"Graph community {community_id}: {len(members)} suppliers, "
        f"avg SCRI {avg_risk:.0%}. Countries: {', '.join(countries) or 'n/a'}. "
        f"Industries: {', '.join(industries) or 'n/a'}. "
        f"Key suppliers: {', '.join(names) or 'none'}."
    )


def index_graph_communities(limit: int = 200) -> int:
    """Build community summaries and upsert to meridian_graph_communities."""
    rows = _fetch_supplier_subgraph(limit=limit)
    if not rows:
        logger.warning("graph_communities_empty")
        return 0

    communities = _detect_communities(rows)
    docs = []
    for community_id, members in communities.items():
        if not members:
            continue
        summary = _community_summary(community_id, members)
        risks = [float(m.get("risk_score") or 0) for m in members]
        docs.append(
            {
                "id": community_id,
                "text": summary,
                "source": f"graph-community/{community_id}",
                "metadata": {
                    "supplier_count": len(members),
                    "avg_risk": round(sum(risks) / len(risks), 4) if risks else 0,
                    "countries": sorted(
                        {m.get("country_iso") for m in members if m.get("country_iso")}
                    ),
                },
            }
        )
    return upsert_documents(RagCollection.GRAPH_COMMUNITIES, docs)


def main() -> int:
    store = get_qdrant_store()
    if not store.is_available:
        logger.warning("qdrant_index_skipped", message="Qdrant unavailable")
        return 0

    try:
        get_neo4j_client()
    except Exception as exc:
        logger.warning("neo4j_unavailable", error=str(exc))
        return 0

    count = index_graph_communities()
    logger.info("graph_communities_indexed", count=count)
    print(f"Indexed {count} graph communities into Qdrant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
