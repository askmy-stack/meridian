"""Unit tests for graph embedding alternative supplier recommender."""

from __future__ import annotations

import pytest

from unittest.mock import patch

from src.intelligence.graph_embeddings import (
    build_supplier_embeddings,
    cosine_similarity,
    rank_alternative_suppliers,
)


def test_cosine_similarity_identical() -> None:
    vec = [1.0, 0.0, 0.5]
    assert cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_rank_alternatives_excludes_self() -> None:
    embeddings = {
        "sup-a": type("E", (), {
            "supplier_id": "sup-a",
            "name": "Alpha",
            "vector": [1.0, 0.0, 0.0],
            "risk_score": 0.8,
            "industry": "electronics",
            "country_iso": "TW",
        })(),
        "sup-b": type("E", (), {
            "supplier_id": "sup-b",
            "name": "Beta",
            "vector": [0.9, 0.1, 0.0],
            "risk_score": 0.4,
            "industry": "electronics",
            "country_iso": "SG",
        })(),
        "sup-c": type("E", (), {
            "supplier_id": "sup-c",
            "name": "Gamma",
            "vector": [0.0, 1.0, 0.0],
            "risk_score": 0.2,
            "industry": "energy",
            "country_iso": "US",
        })(),
    }
    results = rank_alternative_suppliers("sup-a", limit=3, embeddings=embeddings)
    ids = [r["supplier_id"] for r in results]
    assert "sup-a" not in ids
    assert ids[0] == "sup-b"
    assert results[0]["method"] == "node2vec_stub"


def test_build_embeddings_graceful_when_neo4j_down() -> None:
    with patch(
        "src.intelligence.graph_embeddings._fetch_supplier_subgraph",
        return_value=[],
    ):
        index = build_supplier_embeddings()
    assert index == {}
