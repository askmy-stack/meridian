"""Context budget helpers — dedupe citations and cap total character length."""

from __future__ import annotations

from typing import Any, Dict, List, TypeVar

DEFAULT_CONTEXT_CHAR_BUDGET = 4000

T = TypeVar("T", bound=Dict[str, Any])


def dedupe_by_source(items: List[T], source_key: str = "source") -> List[T]:
    """Keep first occurrence per source identifier."""
    seen: set[str] = set()
    deduped: List[T] = []
    for item in items:
        key = str(item.get(source_key, ""))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def cap_context_chars(texts: List[str], budget: int = DEFAULT_CONTEXT_CHAR_BUDGET) -> List[str]:
    """Truncate list of context strings to fit within character budget."""
    result: List[str] = []
    used = 0
    for text in texts:
        if not text:
            continue
        remaining = budget - used
        if remaining <= 0:
            break
        snippet = text[:remaining]
        result.append(snippet)
        used += len(snippet)
    return result


def build_bounded_context(
    texts: List[str],
    *,
    budget: int = DEFAULT_CONTEXT_CHAR_BUDGET,
) -> str:
    """Join deduplicated, budget-capped context strings."""
    capped = cap_context_chars(texts, budget=budget)
    return "\n".join(capped)
