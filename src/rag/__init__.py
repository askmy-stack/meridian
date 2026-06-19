"""RAG infrastructure — Qdrant vector store + grounded copilot retrieval."""

from .collections import RagCollection, search_all, search_routed, upsert_documents
from .embedder import Embedder, get_embedder
from .qdrant_client import QdrantStore, get_qdrant_store

__all__ = [
    "Embedder",
    "QdrantStore",
    "RagCollection",
    "get_embedder",
    "get_qdrant_store",
    "search_all",
    "search_routed",
    "upsert_documents",
]
