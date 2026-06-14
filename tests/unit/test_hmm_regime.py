"""Unit tests for Phase C — HMM regime detector."""

from __future__ import annotations

import numpy as np

from src.intelligence.hmm_regime import (
    REGIME_LABELS,
    assess_regime_from_series,
    assess_region_regime,
    regime_summary_all_regions,
)


def test_assess_regime_stable_series() -> None:
    rates = [0.15 + i * 0.01 for i in range(14)]
    result = assess_regime_from_series("zone-suez", rates)
    assert result.regime in REGIME_LABELS
    assert result.history_days == 14
    assert 0.0 <= result.confidence <= 1.0


def test_assess_regime_crisis_series() -> None:
    rates = [float(0.85 + np.random.default_rng(1).normal(0, 0.02)) for _ in range(20)]
    result = assess_regime_from_series("zone-ukraine", rates)
    assert result.regime in REGIME_LABELS
    assert result.event_rate >= 0.7


def test_assess_regime_empty_series() -> None:
    result = assess_regime_from_series("zone-test", [])
    assert result.method == "insufficient_data"
    assert result.regime == "stable"


def test_assess_region_regime_synthetic() -> None:
    result = assess_region_regime("zone-taiwan-strait", days=21)
    assert result.region_id == "zone-taiwan-strait"
    assert result.regime in REGIME_LABELS
    assert result.history_days == 21


def test_regime_summary_all_regions() -> None:
    summary = regime_summary_all_regions(days=14)
    assert summary["summary"]["total"] >= 5
    assert len(summary["regions"]) == summary["summary"]["total"]
