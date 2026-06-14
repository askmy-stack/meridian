"""Grounded copilot — RAG retrieval + structured Neo4j facts (D-006: no LLM risk scores)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog

from ..graph import get_neo4j_client
from .collections import search_all

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

# Patterns that ask for numeric risk — must be answered only from graph context
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


def _graph_context(client: Any) -> Tuple[List[str], List[str], Dict[str, float]]:
    """Return supplier names, fact strings, and known risk scores from Neo4j."""
    suppliers = client.execute_query(
        """
        MATCH (s:Supplier)
        WHERE s.risk_score >= 0.7
        RETURN s.name AS name, s.risk_score AS risk
        ORDER BY s.risk_score DESC
        LIMIT 5
        """
    )
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
    names = [r["name"] for r in suppliers]
    risk_map = {r["name"]: float(r["risk"]) for r in suppliers if r.get("risk") is not None}
    facts = [
        f"{row.get('suppliers', 0)} suppliers in graph",
        f"{row.get('events', 0)} events materialized",
        f"{row.get('affected', 0)} suppliers linked to events",
    ]
    return names, facts, risk_map


def _match_scenario(question: str) -> Optional[str]:
    q = question.lower()
    for scenario_id, keywords in SCENARIO_KEYWORDS.items():
        if any(word in q for word in keywords):
            return scenario_id
    return None


def _retrieve_citations(question: str, limit: int = 5) -> List[Citation]:
    hits = search_all(question, limit_per_collection=2)[:limit]
    return [
        Citation(
            source=hit.get("source", "unknown"),
            text=hit.get("text", "")[:400],
            collection=hit.get("collection", ""),
            score=hit.get("score"),
        )
        for hit in hits
        if hit.get("text")
    ]


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


def _ollama_compose(question: str, context: str) -> Optional[str]:
    """Optional Ollama synthesis — must not invent risk scores."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma2:2b")
    try:
        import requests

        prompt = (
            "You are a supply chain risk analyst copilot. Answer ONLY from the context below. "
            "NEVER invent numeric risk scores or SCRI percentages. "
            "If context lacks data, say you don't know.\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return str(resp.json().get("response", "")).strip()
    except Exception as exc:
        logger.info("ollama_compose_skipped", error=str(exc))
        return None


def _openai_compose(question: str, context: str) -> Optional[str]:
    """Optional OpenAI synthesis — must not invent risk scores."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        import requests

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer ONLY from provided context. Never invent risk scores. "
                            "Cite sources when possible."
                        ),
                    },
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
                ],
                "max_tokens": 400,
            },
            timeout=30,
        )
        resp.raise_for_status()
        choices = resp.json().get("choices") or []
        if choices:
            return str(choices[0]["message"]["content"]).strip()
    except Exception as exc:
        logger.info("openai_compose_skipped", error=str(exc))
    return None


def _llm_compose(question: str, context: str) -> Optional[str]:
    provider = os.getenv("LLM_PROVIDER", "stub").lower()
    if provider == "ollama":
        return _ollama_compose(question, context)
    if provider == "openai":
        return _openai_compose(question, context)
    return None


def answer_copilot(question: str) -> CopilotResult:
    """Run grounded copilot pipeline."""
    client = get_neo4j_client()
    names, graph_facts, risk_map = _graph_context(client)
    scenario_id = _match_scenario(question)
    citations = _retrieve_citations(question)

    context_parts = graph_facts + [c.text for c in citations]
    context = "\n".join(context_parts)

    llm_answer = _llm_compose(question, context)
    if llm_answer:
        # Strip any hallucinated percentage risk claims not in risk_map
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

    return CopilotResult(
        answer=answer,
        suggested_scenario_id=scenario_id,
        related_suppliers=names,
        grounded=grounded,
        disclaimer=COPILOT_DISCLAIMER,
        graph_facts=graph_facts,
        citations=citations,
    )
