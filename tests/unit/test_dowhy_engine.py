"""Unit tests for DoWhy causal wrapper."""

from __future__ import annotations

from src.causal.dowhy_engine import assess_event_supplier_link


def test_causal_insufficient_data() -> None:
    result = assess_event_supplier_link([0.9], [0.1])
    assert result.causal_claim_allowed is False
    assert result.method == "insufficient_data"


def test_causal_association_only_with_small_sample() -> None:
    severities = [0.5 + i * 0.05 for i in range(10)]
    deltas = [0.1 + i * 0.03 for i in range(10)]
    result = assess_event_supplier_link(severities, deltas)
    assert result.method == "association_only"
    assert result.effect_size is not None
    assert result.sample_count == 10
    assert result.correlation_ci_lower is not None
    assert result.correlation_ci_upper is not None
    assert result.correlation_ci_lower <= result.effect_size <= result.correlation_ci_upper
