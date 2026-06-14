#!/usr/bin/env python3
"""Index Neo4j events, supplier names, and METRICS.md into Qdrant RAG collections."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import structlog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.graph import get_neo4j_client  # noqa: E402
from src.rag.collections import RagCollection, upsert_documents  # noqa: E402
from src.rag.qdrant_client import get_qdrant_store  # noqa: E402

logger = structlog.get_logger(__name__)
METRICS_PATH = ROOT / "docs" / "METRICS.md"


def _chunk_markdown(text: str, chunk_size: int = 600) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 2 <= chunk_size:
            buf = f"{buf}\n\n{para}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = para
    if buf:
        chunks.append(buf)
    return chunks


def index_events(client: object) -> int:
    rows = client.execute_query(  # type: ignore[union-attr]
        """
        MATCH (e:Event)
        RETURN e.id AS id, e.title AS title, e.description AS description,
               e.region AS region, e.event_type AS event_type
        LIMIT 500
        """
    )
    docs = []
    for row in rows:
        text = f"{row.get('title', '')}. {row.get('description', '')} Region: {row.get('region', '')}"
        docs.append(
            {
                "id": row["id"],
                "text": text.strip(),
                "metadata": {
                    "event_type": row.get("event_type"),
                    "region": row.get("region"),
                },
            }
        )
    return upsert_documents(RagCollection.EVENTS, docs)


def index_suppliers(client: object) -> int:
    rows = client.execute_query(  # type: ignore[union-attr]
        """
        MATCH (s:Supplier)
        RETURN s.id AS id, s.name AS name, s.country_iso AS country,
               s.industry AS industry, s.risk_score AS risk_score
        LIMIT 500
        """
    )
    docs = []
    for row in rows:
        risk = row.get("risk_score")
        risk_note = f" SCRI (graph): {int(float(risk) * 100)}%" if risk is not None else ""
        text = (
            f"Supplier {row.get('name')} ({row.get('country', '')}) "
            f"industry {row.get('industry', 'unknown')}.{risk_note}"
        )
        docs.append(
            {
                "id": row["id"],
                "text": text.strip(),
                "metadata": {
                    "country": row.get("country"),
                    "industry": row.get("industry"),
                },
            }
        )
    return upsert_documents(RagCollection.SUPPLIERS, docs)


def index_methodology() -> int:
    if not METRICS_PATH.exists():
        logger.warning("metrics_md_missing", path=str(METRICS_PATH))
        return 0
    text = METRICS_PATH.read_text(encoding="utf-8")
    chunks = _chunk_markdown(text)
    docs = [
        {
            "id": f"metrics-chunk-{i}",
            "text": chunk,
            "source": "docs/METRICS.md",
            "metadata": {"chunk_index": i},
        }
        for i, chunk in enumerate(chunks)
    ]
    return upsert_documents(RagCollection.METHODOLOGY, docs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-neo4j", action="store_true", help="Index methodology only")
    args = parser.parse_args()

    store = get_qdrant_store()
    if not store.is_available:
        logger.warning("qdrant_index_skipped", message="Qdrant unavailable — exiting 0 for graceful skip")
        return 0

    total = index_methodology()

    if not args.skip_neo4j:
        try:
            client = get_neo4j_client()
            total += index_events(client)
            total += index_suppliers(client)
        except Exception as exc:
            logger.warning("neo4j_index_partial", error=str(exc))

    logger.info("rag_index_complete", documents=total)
    print(f"Indexed {total} documents into Qdrant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
