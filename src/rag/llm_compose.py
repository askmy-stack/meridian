"""Shared LLM composition helpers — D-006: never invent risk scores."""

from __future__ import annotations

import os
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


def ollama_compose(question: str, context: str) -> Optional[str]:
    """Optional Ollama synthesis — must not invent risk scores."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma2:2b")
    try:
        import requests

        prompt = (
            "You are a supply chain risk analyst. Answer ONLY from the context below. "
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


def openai_compose(question: str, context: str) -> Optional[str]:
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


def llm_compose(question: str, context: str) -> Optional[str]:
    """Compose prose from context using configured LLM provider."""
    provider = os.getenv("LLM_PROVIDER", "stub").lower()
    if provider == "ollama":
        return ollama_compose(question, context)
    if provider == "openai":
        return openai_compose(question, context)
    return None
