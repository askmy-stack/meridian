#!/usr/bin/env python3
"""Fetch World Bank WGI political stability scores and cache locally."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence.feature_builder import COUNTRY_STABILITY

logger = structlog.get_logger(__name__)

CACHE_PATH = Path(__file__).parent.parent / "data" / "wgi_stability.json"
WGI_INDICATOR = "PV.EST"
WORLD_BANK_COUNTRIES = sorted(COUNTRY_STABILITY.keys())


def _fetch_country_score(country_iso: str) -> float | None:
    """Fetch latest PV.EST score for a country from the World Bank API."""
    import urllib.error
    import urllib.request

    url = (
        "https://api.worldbank.org/v2/country/"
        f"{country_iso}/indicator/{WGI_INDICATOR}?format=json&date=2018:2023&per_page=5"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("wgi_fetch_failed", country=country_iso, error=str(exc))
        return None

    if not isinstance(payload, list) or len(payload) < 2:
        return None

    entries: List[Dict[str, Any]] = payload[1] or []
    for entry in entries:
        value = entry.get("value")
        if value is not None:
            # WGI PV.EST ranges roughly -2.5..+2.5 — normalize to 0..1
            normalized = max(0.0, min(1.0, (float(value) + 2.5) / 5.0))
            return round(normalized, 4)
    return None


def build_cache(*, use_network: bool = True) -> Dict[str, Any]:
    """Build WGI cache dict, falling back to static table when fetch fails."""
    scores: Dict[str, float] = {}
    sources: Dict[str, str] = {}

    for iso in WORLD_BANK_COUNTRIES:
        fetched = _fetch_country_score(iso) if use_network else None
        if fetched is not None:
            scores[iso] = fetched
            sources[iso] = "live_wgi"
        else:
            scores[iso] = COUNTRY_STABILITY[iso]
            sources[iso] = "static_fallback"

    return {
        "indicator": WGI_INDICATOR,
        "indicator_name": "Political Stability and Absence of Violence/Terrorism",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "scores": scores,
        "sources": sources,
        "live_count": sum(1 for s in sources.values() if s == "live_wgi"),
    }


def main() -> int:
    cache = build_cache(use_network=True)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    print(f"WGI cache written to {CACHE_PATH} ({cache['live_count']} live scores)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
