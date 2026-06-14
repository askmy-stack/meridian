"""Unit tests for WGI cache loading in feature builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.intelligence.feature_builder as fb
from src.intelligence.feature_builder import (
    COUNTRY_STABILITY,
    political_stability_for_country,
)


def test_political_stability_uses_cache_or_fallback() -> None:
    score, source = political_stability_for_country("US")
    assert 0.0 <= score <= 1.0
    assert source in ("live_wgi", "static_fallback")


def test_political_stability_unknown_country_defaults() -> None:
    score, source = political_stability_for_country("ZZ")
    assert score == 0.5
    assert source == "static_fallback"


def test_wgi_cache_covers_demo_countries() -> None:
    for iso in ("CN", "TW", "US", "DE"):
        score, _ = political_stability_for_country(iso)
        assert score == COUNTRY_STABILITY[iso] or 0.0 <= score <= 1.0


def test_wgi_cache_hit_uses_live_wgi_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "wgi_stability.json"
    cache.write_text(
        json.dumps(
            {
                "scores": {"US": 0.91},
                "sources": {"US": "live_wgi"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(fb, "WGI_CACHE_PATH", cache)
    score, source = fb.political_stability_for_country("US")
    assert score == 0.91
    assert source == "live_wgi"
