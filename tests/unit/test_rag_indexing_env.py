"""Tests for RAG indexing env loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.rag.env import REPO_ROOT, ensure_rag_env, reset_rag_env_state


@pytest.fixture(autouse=True)
def _clean_rag_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate env loading and singleton state between tests."""
    reset_rag_env_state()
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("RAG_EMBED_MODE", raising=False)
    yield
    reset_rag_env_state()


def test_ensure_rag_env_loads_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QDRANT_URL=http://qdrant-from-dotenv:6333\nRAG_EMBED_MODE=hash\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("src.rag.env.REPO_ROOT", tmp_path)
    reset_rag_env_state()

    ensure_rag_env()

    assert os.getenv("QDRANT_URL") == "http://qdrant-from-dotenv:6333"
    assert os.getenv("RAG_EMBED_MODE") == "hash"


def test_ensure_rag_env_does_not_override_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("QDRANT_URL=http://from-file:6333\n", encoding="utf-8")
    monkeypatch.setenv("QDRANT_URL", "http://from-shell:6333")
    monkeypatch.setattr("src.rag.env.REPO_ROOT", tmp_path)
    reset_rag_env_state()

    ensure_rag_env()

    assert os.getenv("QDRANT_URL") == "http://from-shell:6333"


def test_get_qdrant_store_reads_dotenv_before_singleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("QDRANT_URL=http://qdrant-singleton:6333\n", encoding="utf-8")
    monkeypatch.setattr("src.rag.env.REPO_ROOT", tmp_path)
    reset_rag_env_state()

    from src.rag.qdrant_client import get_qdrant_store

    store = get_qdrant_store()

    assert store.url == "http://qdrant-singleton:6333"


def test_get_embedder_reads_dotenv_before_singleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("RAG_EMBED_MODE=hash\n", encoding="utf-8")
    monkeypatch.setattr("src.rag.env.REPO_ROOT", tmp_path)
    reset_rag_env_state()

    from src.rag.embedder import get_embedder

    embedder = get_embedder()

    assert embedder.force_hash is True
    assert embedder.mode == "hash"


def test_indexing_module_resolves_repo_root_docs() -> None:
    from src.rag import indexing

    assert indexing.ROOT == REPO_ROOT
    assert indexing.METRICS_PATH == REPO_ROOT / "docs" / "METRICS.md"
    assert indexing.METRICS_PATH.exists()
