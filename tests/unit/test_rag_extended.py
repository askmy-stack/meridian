"""Unit tests for extended RAG layer — routing, communities, digest citations."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, generate_weekly_digest
from src.rag.collections import RagCollection, _route_collections, search_routed
from src.rag.context_budget import cap_context_chars, dedupe_by_source

client = TestClient(app)


@pytest.fixture(autouse=True)
def _hash_embed_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_EMBED_MODE", "hash")
    monkeypatch.setenv("LLM_PROVIDER", "stub")


def test_route_methodology_keywords() -> None:
    routed = _route_collections("How is SCRI calculated?")
    collections = [c for c, _ in routed]
    assert RagCollection.METHODOLOGY in collections
    assert collections[0] == RagCollection.METHODOLOGY


def test_route_backtest_keywords() -> None:
    routed = _route_collections("Tell me about the Suez Ever Given backtest")
    collections = [c for c, _ in routed]
    assert RagCollection.BACKTESTS in collections


def test_dedupe_by_source() -> None:
    items = [
        {"source": "a", "text": "one"},
        {"source": "a", "text": "dup"},
        {"source": "b", "text": "two"},
    ]
    deduped = dedupe_by_source(items)
    assert len(deduped) == 2
    assert deduped[0]["text"] == "one"


def test_cap_context_chars() -> None:
    texts = ["a" * 3000, "b" * 2000]
    capped = cap_context_chars(texts, budget=4000)
    assert sum(len(t) for t in capped) <= 4000


def test_search_routed_empty_when_qdrant_down() -> None:
    with patch("src.rag.collections.get_qdrant_store") as mock_store:
        mock_store.return_value.is_available = False
        assert search_routed("Red Sea risk") == []


def test_index_graph_communities_stub() -> None:
    from scripts.index_graph_communities import _community_summary, _detect_communities

    rows = [
        {
            "id": "s1",
            "name": "Fab A",
            "risk_score": 0.8,
            "country_iso": "TW",
            "industry": "semiconductors",
            "neighbors": ["s2"],
        },
        {
            "id": "s2",
            "name": "Fab B",
            "risk_score": 0.6,
            "country_iso": "TW",
            "industry": "semiconductors",
            "neighbors": ["s1"],
        },
    ]
    communities = _detect_communities(rows)
    assert communities
    summary = _community_summary("community-0", rows)
    assert "suppliers" in summary.lower()


@pytest.mark.asyncio
async def test_weekly_digest_has_citations_field() -> None:
    mock_client = MagicMock()
    mock_client.execute_query.side_effect = [
        [{"type": "conflict", "count": 3}],
        [{"id": "s1", "name": "Fab A", "risk": 0.9}],
        [{"total_events": 3, "affected_suppliers": 2}],
    ]
    with patch("src.api.main.get_neo4j_client", return_value=mock_client), patch(
        "src.rag.collections.search_routed",
        return_value=[
            {
                "source": "docs/METRICS.md",
                "text": "SCRI methodology overview",
                "collection": "meridian_methodology",
                "score": 0.9,
            }
        ],
    ):
        digest = await generate_weekly_digest()

    assert "citations" in digest
    assert "narrative_type" in digest
    assert digest["narrative_type"] in ("template", "rag")


def test_supplier_explanation_related_corpus_field() -> None:
    from src.api.main import _supplier_related_corpus

    with patch("src.rag.collections.search_collection", return_value=[]):
        corpus = _supplier_related_corpus("Test Supplier", "TW")
    assert isinstance(corpus, list)


def test_rag_indexer_graceful_skip() -> None:
    from src.consumers.rag_indexer import RagIndexerConsumer

    consumer = RagIndexerConsumer()
    with patch("src.consumers.rag_indexer.get_qdrant_store") as mock_store:
        mock_store.return_value.is_available = False
        assert consumer.index_event({"event_id": "e1", "description": "test"}) is False
        assert consumer.stats["skipped"] == 1
