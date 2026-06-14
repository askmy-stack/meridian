"""Causal context helpers for pipeline-generated alerts (D-005)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from .dowhy_engine import CausalAssessment, assess_event_supplier_link

DEFAULT_CAUSAL_PAIR_LIMIT = 100


def causal_pair_limit() -> int:
    """Return max Event→Supplier pairs to fetch for causal assessment."""
    return int(os.getenv("CAUSAL_PAIR_LIMIT", str(DEFAULT_CAUSAL_PAIR_LIMIT)))


def fetch_event_supplier_pairs(
    client: Any,
    *,
    limit: int | None = None,
) -> Tuple[List[float], List[float]]:
    """Load paired event severity and supplier SCRI from the graph."""
    pair_limit = limit if limit is not None else causal_pair_limit()
    rows = client.execute_query(
        """
        MATCH (e:Event)-[:AFFECTS]->(s:Supplier)
        WHERE e.severity IS NOT NULL AND s.risk_score IS NOT NULL
        RETURN e.severity AS severity, s.risk_score AS risk_score
        ORDER BY e.ingested_at DESC
        LIMIT $limit
        """,
        {"limit": pair_limit},
    )
    severities = [float(row["severity"]) for row in rows]
    risks = [float(row["risk_score"]) for row in rows]
    return severities, risks


def assess_pipeline_causality(client: Any) -> CausalAssessment:
    """Run DoWhy / association-only assessment on recent graph pairs."""
    severities, risks = fetch_event_supplier_pairs(client)
    return assess_event_supplier_link(severities, risks)


def format_alert_causal_summary(assessment: CausalAssessment) -> str:
    """Human-readable causal disclaimer for alert impact summaries."""
    if assessment.causal_claim_allowed:
        return (
            f"Causal link verified (DoWhy, effect={assessment.effect_size}). "
            f"{assessment.disclaimer}"
        )
    if assessment.method == "association_only":
        return (
            f"Association only — correlation {assessment.effect_size} "
            f"(not verified causation). {assessment.disclaimer}"
        )
    return assessment.disclaimer


def causal_fields_for_alert(assessment: CausalAssessment) -> Dict[str, Any]:
    """Wire-format causal metadata attached to Alert payloads."""
    fields = {
        "causal_claim_allowed": assessment.causal_claim_allowed,
        "causal_method": assessment.method,
        "causal_effect_size": assessment.effect_size,
        "causal_disclaimer": assessment.disclaimer,
        "causal_sample_count": assessment.sample_count,
    }
    if assessment.correlation_ci_lower is not None:
        fields["causal_correlation_ci_lower"] = assessment.correlation_ci_lower
    if assessment.correlation_ci_upper is not None:
        fields["causal_correlation_ci_upper"] = assessment.correlation_ci_upper
    return fields
