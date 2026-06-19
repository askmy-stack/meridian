"""Grounded copilot — RAG retrieval + structured Neo4j facts (D-006: no LLM risk scores)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog

from ..graph import get_neo4j_client
from .collections import RagCollection, search_routed
from .context_budget import DEFAULT_CONTEXT_CHAR_BUDGET, build_bounded_context, dedupe_by_source
from .llm_compose import llm_compose

logger = structlog.get_logger(__name__)

COPILOT_DISCLAIMER = (
    "Grounded copilot — answers cite retrieved documents and Neo4j graph facts only. "
    "Numeric risk scores come from XGBoost/SCRI, never from the LLM. "
    "Unverified claims are refused."
)

SCENARIO_KEYWORDS = {
    "red-sea-bab-el-mandeb": ("red sea", "houthi", "bab"),
    "taiwan-strait-tension": ("taiwan", "semiconductor", "chip"),
    "suez-canal-blockage": ("suez", "canal"),
    "russia-ukraine-supply": ("ukraine", "russia"),
    "us-iran-hormuz": ("hormuz", "iran"),
    "china-us-trade": ("china", "tariff", "export control"),
}

REGION_KEYWORDS = {
    "red sea": "Red Sea",
    "taiwan": "Taiwan",
    "suez": "Suez",
    "ukraine": "Ukraine",
    "russia": "Russia",
    "hormuz": "Persian Gulf",
    "china": "China",
    "europe": "Europe",
    "semiconductor": "semiconductor",
}

RISK_NUMBER_PATTERN = re.compile(
    r"\b(\d{1,3})\s*%\s*(risk|scri|score)|"
    r"risk\s*(score|level)\s*(is|of|at)\s*(\d+\.?\d*)|"
    r"what\s+is\s+the\s+risk\s+score",
    re.IGNORECASE,
)


@dataclass
class Citation:
    """Retrieved source for copilot grounding."""

    source: str
    text: str
    collection: str
    score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "text": self.text,
            "collection": self.collection,
            "score": self.score,
        }


@dataclass
class CopilotResult:
    """Structured copilot response."""

    answer: str
    suggested_scenario_id: Optional[str] = None
    related_suppliers: List[str] = field(default_factory=list)
    grounded: bool = True
    disclaimer: str = COPILOT_DISCLAIMER
    graph_facts: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "suggested_scenario_id": self.suggested_scenario_id,
            "related_suppliers": self.related_suppliers,
            "grounded": self.grounded,
            "disclaimer": self.disclaimer,
            "graph_facts": self.graph_facts,
            "citations": [c.to_dict() for c in self.citations],
            "generated_at": self.generated_at,
        }


def _extract_question_keywords(question: str) -> List[str]:
    """Extract region/supplier tokens from the user question."""
    q = question.lower()
    keywords: List[str] = []
    for token, _label in REGION_KEYWORDS.items():
        if token in q:
            keywords.append(token)
    for word in re.findall(r"[a-z]{4,}", q):
        if word not in keywords:
            keywords.append(word)
    return keywords[:8]


def _graph_context_for_question(
    client: Any,
    question: str,
) -> Tuple[List[str], List[str], Dict[str, float]]:
    """Return supplier names, fact strings, and risk_map tailored to the question."""
    keywords = _extract_question_keywords(question)
    names: List[str] = []
    risk_map: Dict[str, float] = {}

    if keywords:
        for kw in keywords[:3]:
            rows = client.execute_query(
                """
                MATCH (s:Supplier)
                WHERE toLower(s.name) CONTAINS $kw
                   OR toLower(coalesce(s.country_iso, '')) CONTAINS $kw
                   OR toLower(coalesce(s.industry, '')) CONTAINS $kw
                RETURN s.name AS name, s.risk_score AS risk
                ORDER BY s.risk_score DESC
                LIMIT 5
                """,
                {"kw": kw},
            )
            for row in rows:
                name = row.get("name")
                if name and name not in names:
                    names.append(name)
                    if row.get("risk") is not None:
                        risk_map[name] = float(row["risk"])

        event_rows = client.execute_query(
            """
            MATCH (e:Event)-[:AFFECTS]->(s:Supplier)
            WHERE any(kw IN $keywords WHERE
                toLower(coalesce(e.region, '')) CONTAINS kw
                OR toLower(coalesce(e.title, '')) CONTAINS kw
            )
            RETURN DISTINCT e.title AS title, e.region AS region,
                   collect(DISTINCT s.name)[0..3] AS suppliers
            LIMIT 5
            """,
            {"keywords": keywords},
        )
        event_facts = [
            f"Event '{r.get('title', '')}' in {r.get('region', '')} "
            f"affects {', '.join(r.get('suppliers') or [])}"
            for r in event_rows
            if r.get("title")
        ]
    else:
        event_facts = []

    if not names:
        suppliers = client.execute_query(
            """
            MATCH (s:Supplier)
            WHERE s.risk_score >= 0.7
            RETURN s.name AS name, s.risk_score AS risk
            ORDER BY s.risk_score DESC
            LIMIT 5
            """
        )
        for row in suppliers:
            name = row.get("name")
            if name:
                names.append(name)
                if row.get("risk") is not None:
                    risk_map[name] = float(row["risk"])

    choke_rows = client.execute_query(
        """
        MATCH (c:Chokepoint)
        WHERE any(kw IN $keywords WHERE toLower(c.name) CONTAINS kw)
        RETURN c.name AS name, c.region AS region
        LIMIT 3
        """,
        {"keywords": keywords or ["suez", "red", "taiwan"]},
    )
    choke_facts = [
        f"Chokepoint {r.get('name')} ({r.get('region', '')})" for r in choke_rows if r.get("name")
    ]

    stats = client.execute_query(
        """
        OPTIONAL MATCH (s:Supplier) WITH count(s) AS suppliers
        OPTIONAL MATCH (e:Event) WITH suppliers, count(e) AS events
        OPTIONAL MATCH (s2:Supplier)<-[:AFFECTS]-(:Event) WITH suppliers, events,
             count(DISTINCT s2) AS affected
        RETURN suppliers, events, affected
        """
    )
    row = stats[0] if stats else {}
    facts = [
        f"{row.get('suppliers', 0)} suppliers in graph",
        f"{row.get('events', 0)} events materialized",
        f"{row.get('affected', 0)} suppliers linked to events",
    ]
    facts.extend(event_facts[:3])
    facts.extend(choke_facts[:2])
    return names[:8], facts, risk_map


def _match_scenario(question: str) -> Optional[str]:
    q = question.lower()
    for scenario_id, kws in SCENARIO_KEYWORDS.items():
        if any(word in q for word in kws):
            return scenario_id
    return None


def _retrieve_citations(question: str, limit: int = 5) -> Tuple[List[Citation], float]:
    """Retrieve routed citations; return (citations, retrieval_ms)."""
    t0 = time.perf_counter()
    hits = search_routed(question, limit=limit)
    deduped = dedupe_by_source(hits, source_key="source")
    citations = [
        Citation(
            source=hit.get("source", "unknown"),
            text=hit.get("text", "")[:400],
            collection=hit.get("collection", ""),
            score=hit.get("score"),
        )
        for hit in deduped
        if hit.get("text")
    ]
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return citations, elapsed_ms


def _format_risk_from_context(question: str, risk_map: Dict[str, float]) -> Optional[str]:
    """Answer numeric risk questions only when scores exist in graph context."""
    if not RISK_NUMBER_PATTERN.search(question):
        return None
    if not risk_map:
        return (
            "I cannot provide numeric risk scores — no supplier SCRI values are in the "
            "current graph context. Run `make score-suppliers` to populate XGBoost scores."
        )
    parts = [f"{name}: {int(score * 100)}% SCRI (from graph)" for name, score in risk_map.items()]
    return "Known SCRI values from the knowledge graph: " + "; ".join(parts) + "."


def _stub_compose(
    question: str,
    scenario_id: Optional[str],
    names: List[str],
    graph_facts: List[str],
    citations: List[Citation],
    risk_map: Dict[str, float],
) -> Tuple[str, bool]:
    """Template answer without external LLM — safe for tests and demo."""
    risk_answer = _format_risk_from_context(question, risk_map)
    if risk_answer:
        return risk_answer, True

    cite_snippet = ""
    if citations:
        cite_snippet = f" Retrieved: {citations[0].text[:120]}…"

    if scenario_id:
        answer = (
            f"Based on graph data ({', '.join(graph_facts)}), I recommend the "
            f"{scenario_id.replace('-', ' ')} simulator preset. "
            f"Top exposed suppliers: {', '.join(names) if names else 'none seeded'}.{cite_snippet}"
        )
        return answer, True

    if names or citations:
        answer = (
            "I don't have a matching scenario preset for that question. "
            f"Graph facts: {', '.join(graph_facts)}. "
            f"High-risk suppliers in context: {', '.join(names) if names else 'none'}.{cite_snippet} "
            "Try Red Sea, Taiwan semiconductors, Suez, or Ukraine supply shocks."
        )
        return answer, bool(names or citations)

    return (
        "I don't know — insufficient graph and corpus context. "
        "Run `make seed-all` and `make index-rag`, then ask about a supported scenario keyword.",
        False,
    )


def answer_copilot(question: str) -> CopilotResult:
    """Run grounded copilot pipeline."""
    client = get_neo4j_client()
    names, graph_facts, risk_map = _graph_context_for_question(client, question)
    scenario_id = _match_scenario(question)
    citations, retrieval_ms = _retrieve_citations(question)

    context = build_bounded_context(
        graph_facts + [c.text for c in citations],
        budget=DEFAULT_CONTEXT_CHAR_BUDGET,
    )

    llm_answer = llm_compose(question, context)
    if llm_answer:
        if RISK_NUMBER_PATTERN.search(llm_answer) and not risk_map:
            llm_answer = _format_risk_from_context(question, risk_map) or (
                "I cannot confirm numeric risk scores from the available context."
            )
        answer = re.sub(r"\*\*", "", llm_answer)
        grounded = bool(graph_facts or citations)
    else:
        answer, grounded = _stub_compose(
            question, scenario_id, names, graph_facts, citations, risk_map
        )

    answer = re.sub(r"\*\*", "", answer)
    grounded = grounded and bool(citations or graph_facts)

    logger.info(
        "copilot_answer",
        grounded=grounded,
        citations_count=len(citations),
        retrieval_ms=round(retrieval_ms, 2),
        scenario_id=scenario_id,
    )

    return CopilotResult(
        answer=answer,
        suggested_scenario_id=scenario_id,
        related_suppliers=names,
        grounded=grounded,
        disclaimer=COPILOT_DISCLAIMER,
        graph_facts=graph_facts,
        citations=citations,
    )
