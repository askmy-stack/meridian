"""Load Meridian .env for RAG indexing and retrieval."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
_env_loaded = False


def ensure_rag_env() -> Path:
    """Load repo-root ``.env`` once without overriding existing env vars."""
    global _env_loaded
    if not _env_loaded:
        load_dotenv(REPO_ROOT / ".env")
        _env_loaded = True
    return REPO_ROOT


def reset_rag_env_state() -> None:
    """Reset env-load flag and RAG singletons (tests only)."""
    global _env_loaded
    _env_loaded = False
    from . import embedder, qdrant_client

    embedder._embedder = None  # type: ignore[attr-defined]
    qdrant_client._store = None  # type: ignore[attr-defined]
