"""Reusable RAG corpus indexing — Neo4j entities and static docs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from .collections import RagCollection, upsert_documents

logger = structlog.get_logger(__name__)

ROOT = Path(__file__).resolve().parents[2]
METRICS_PATH = ROOT / "docs" / "METRICS.md"
LIMITATIONS_PATH = ROOT / "docs" / "LIMITATIONS.md"
CAUSAL_SCOPE_PATH = ROOT / "docs" / "CAUSAL_SCOPE.md"


def chunk_markdown(text: str, chunk_size: int = 600) -> List[str]:
    """Split markdown into paragraph-bounded chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
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


def index_events(client: object, limit: int = 500) -> int:
    """Index Neo4j Event nodes into meridian_events."""
    rows = client.execute_query(  # type: ignore[union-attr]
        """
        MATCH (e:Event)
        RETURN e.id AS id, e.title AS title, e.description AS description,
               e.region AS region, e.event_type AS event_type
        LIMIT $limit
        """,
        {"limit": limit},
    )
    docs = []
    for row in rows:
        text = (
            f"{row.get('title', '')}. {row.get('description', '')} "
            f"Region: {row.get('region', '')}"
        )
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


def index_suppliers(client: object, limit: int = 500) -> int:
    """Index Neo4j Supplier nodes into meridian_suppliers."""
    rows = client.execute_query(  # type: ignore[union-attr]
        """
        MATCH (s:Supplier)
        RETURN s.id AS id, s.name AS name, s.country_iso AS country,
               s.industry AS industry, s.risk_score AS risk_score
        LIMIT $limit
        """,
        {"limit": limit},
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


def index_methodology_docs() -> int:
    """Index METRICS.md, LIMITATIONS.md, and CAUSAL_SCOPE.md into methodology collection."""
    total = 0
    for path in (METRICS_PATH, LIMITATIONS_PATH, CAUSAL_SCOPE_PATH):
        if not path.exists():
            logger.warning("methodology_doc_missing", path=str(path))
            continue
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text)
        docs = [
            {
                "id": f"{path.stem}-chunk-{i}",
                "text": chunk,
                "source": f"docs/{path.name}",
                "metadata": {"chunk_index": i, "doc": path.name},
            }
            for i, chunk in enumerate(chunks)
        ]
        total += upsert_documents(RagCollection.METHODOLOGY, docs)
    return total


def index_scenarios(scenarios: List[Dict[str, Any]]) -> int:
    """Index simulation scenario definitions into meridian_scenarios."""
    docs = []
    for scenario in scenarios:
        sid = scenario.get("id", "")
        mitigations = scenario.get("mitigations") or []
        mitigation_text = "; ".join(mitigations[:3])
        sectors = ", ".join(scenario.get("sectors") or [])
        text = (
            f"{scenario.get('name', sid)}. {scenario.get('description', '')} "
            f"Region: {scenario.get('region', '')}. Sectors: {sectors}. "
            f"Severity: {scenario.get('severity', '')}. Mitigations: {mitigation_text}"
        )
        docs.append(
            {
                "id": sid,
                "text": text.strip(),
                "source": f"simulation/{sid}",
                "metadata": {
                    "region": scenario.get("region"),
                    "event_type": scenario.get("event_type"),
                },
            }
        )
    return upsert_documents(RagCollection.SCENARIOS, docs)


def index_backtests(backtest_scenarios: Dict[str, Dict[str, Any]]) -> int:
    """Index historical backtest case studies into meridian_backtests."""
    docs = []
    for scenario_id, preset in backtest_scenarios.items():
        lessons = "; ".join(preset.get("lessons") or [])
        text = (
            f"{preset.get('title', scenario_id)}. {preset.get('description', '')} "
            f"Region: {preset.get('region', '')}. Lessons: {lessons}"
        )
        docs.append(
            {
                "id": scenario_id,
                "text": text.strip(),
                "source": f"backtest/{scenario_id}",
                "metadata": {
                    "region": preset.get("region"),
                    "severity": preset.get("severity"),
                },
            }
        )
    return upsert_documents(RagCollection.BACKTESTS, docs)


def event_kafka_to_rag_doc(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a normalized Kafka conflict event to a RAG document."""
    event_id = event.get("event_id")
    if not event_id:
        return None
    region = event.get("region") or event.get("country") or "Unknown"
    description = event.get("description") or event.get("notes") or "Geopolitical signal"
    actors = event.get("actors") or []
    title = event.get("title")
    if not title:
        event_type = str(event.get("event_type", "event")).replace("_", " ")
        title = f"{event_type.title()} in {region}"
        if actors:
            title = f"{event_type.title()} — {actors[0]} ({region})"
    text = f"{title}. {description} Region: {region}"
    return {
        "id": event_id,
        "text": text.strip()[:800],
        "metadata": {
            "event_type": event.get("event_type"),
            "region": region,
            "source": event.get("source", "kafka"),
        },
    }
