"""Text embedder — sentence-transformers with deterministic hash fallback."""

from __future__ import annotations

import hashlib
import os
from typing import List, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"
HASH_DIM = 384


class Embedder:
    """Embed text for Qdrant; uses hash fallback when transformers unavailable."""

    def __init__(self, model_name: Optional[str] = None, force_hash: bool = False) -> None:
        self.model_name = model_name or os.getenv("RAG_EMBED_MODEL", DEFAULT_MODEL)
        self.force_hash = force_hash or os.getenv("RAG_EMBED_MODE", "").lower() == "hash"
        self._model: Optional[object] = None
        self._mode = "hash"
        self.logger = logger.bind(component="Embedder", model=self.model_name)

        if not self.force_hash:
            self._try_load_transformers()

    def _try_load_transformers(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._mode = "sentence-transformers"
            self.logger.info("embedder_loaded", mode=self._mode)
        except Exception as exc:
            self.logger.info(
                "embedder_hash_fallback",
                reason=str(exc),
                hint="pip install sentence-transformers or set RAG_EMBED_MODE=hash",
            )
            self._mode = "hash"

    @property
    def vector_size(self) -> int:
        if self._mode == "sentence-transformers" and self._model is not None:
            return int(self._model.get_sentence_embedding_dimension())  # type: ignore[union-attr]
        return HASH_DIM

    @property
    def mode(self) -> str:
        return self._mode

    def embed(self, text: str) -> List[float]:
        """Return a single embedding vector."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        if not texts:
            return []
        if self._mode == "sentence-transformers" and self._model is not None:
            vectors = self._model.encode(texts, normalize_embeddings=True)  # type: ignore[union-attr]
            return [v.tolist() for v in vectors]
        return [self._hash_embed(t) for t in texts]

    def _hash_embed(self, text: str) -> List[float]:
        """Deterministic pseudo-embedding for tests / no-GPU environments."""
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(seed[:8], "big"))
        vec = rng.standard_normal(HASH_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """Singleton embedder."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
