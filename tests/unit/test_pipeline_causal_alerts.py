"""Unit tests for pipeline alert causal context."""

from __future__ import annotations

from src.causal.dowhy_engine import CausalAssessment
from src.causal.pipeline_alerts import (
    causal_fields_for_alert,
    format_alert_causal_summary,
)


def test_format_association_only_summary() -> None:
    assessment = CausalAssessment(
        causal_claim_allowed=False,
        method="association_only",
        effect_size=0.82,
        refutation_passed=False,
        disclaimer="Correlation observed — not a verified causal claim (D-005).",
    )
    summary = format_alert_causal_summary(assessment)
    assert "Association only" in summary
    assert "0.82" in summary


def test_causal_fields_for_alert() -> None:
    assessment = CausalAssessment(
        causal_claim_allowed=False,
        method="insufficient_data",
        effect_size=None,
        refutation_passed=False,
        disclaimer="Not enough paired observations.",
        sample_count=3,
    )
    fields = causal_fields_for_alert(assessment)
    assert fields["causal_method"] == "insufficient_data"
    assert fields["causal_claim_allowed"] is False
    assert fields["causal_disclaimer"] == "Not enough paired observations."
    assert fields["causal_sample_count"] == 3
