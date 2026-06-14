"""Metrics methodology API — SCRI definitions for UI tooltips."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from ...intelligence.model_status import get_risk_model_status

router = APIRouter(prefix="/metrics", tags=["Metrics"])

METHODOLOGY_LIMITATIONS: List[str] = [
    "Default XGBoost may be trained on synthetic labels until a calibrated artifact is deployed.",
    "Several SCRI features use static defaults (weather=0, WGI table, financial heuristics).",
    "SCRI bands are modelled index tiers — not validated actuarial disruption probabilities.",
    "Sector and causal views include demo classification / association-only paths.",
]


def _methodology_payload() -> Dict[str, Any]:
    """Structured metric definitions consumed by the dashboard."""
    model_status = get_risk_model_status(ensure_scorer=False)
    calibration_status = model_status["calibration_status"]

    return {
        "index_name": "SCRI",
        "index_full_name": "Supply Chain Risk Index",
        "scale": "0.0–1.0 (displayed as 0–100%)",
        "description": (
            "Estimated 30-day probability of material supply disruption given "
            "geopolitical signals, network fragility, and operational stress."
        ),
        "model": "XGBoost + SHAP (see DECISIONS D-003)",
        "calibration_status": calibration_status,
        "limitations": METHODOLOGY_LIMITATIONS,
        "display_guidance": {
            "prefer_bands": True,
            "primary_label": "risk band (LOW → CRITICAL)",
            "secondary_label": "modelled index percentage",
            "calibration_sublabel": (
                "Demo calibration"
                if calibration_status == "demo"
                else "Modelled index"
            ),
            "documentation": "docs/LIMITATIONS.md",
        },
        "references": [
            {
                "title": "GDELT Event Codebook — Goldstein Scale",
                "url": "https://www.gdeltproject.org/data/documentation/GDELT-Event_Codebook-V2.0.pdf",
            },
            {
                "title": "World Bank Worldwide Governance Indicators",
                "url": "https://databank.worldbank.org/source/worldwide-governance-indicators",
            },
            {
                "title": "Wagner & Bode (2006) — Supply chain vulnerability",
                "url": "https://doi.org/10.1109/SCOR.2006.320945",
            },
            {
                "title": "Lundberg & Lee (2017) — SHAP",
                "url": "https://arxiv.org/abs/1705.07874",
            },
        ],
        "categories": [
            {"min": 0.0, "max": 0.24, "label": "LOW", "action": "Monitor"},
            {"min": 0.25, "max": 0.49, "label": "MEDIUM", "action": "Quarterly review"},
            {"min": 0.50, "max": 0.74, "label": "HIGH", "action": "Activate contingency"},
            {"min": 0.75, "max": 1.0, "label": "CRITICAL", "action": "Executive escalation"},
        ],
        "kpis": [
            {
                "id": "suppliers_tracked",
                "label": "Suppliers tracked",
                "definition": "Count of Supplier nodes in the Neo4j knowledge graph.",
            },
            {
                "id": "critical_risks",
                "label": "Critical SCRI",
                "definition": "Suppliers with SCRI ≥ 0.75 (CRITICAL band).",
            },
            {
                "id": "active_events",
                "label": "Active events",
                "definition": "Event nodes ingested in the last 7 days from GDELT/ACLED pipeline.",
            },
            {
                "id": "peak_scri",
                "label": "Peak SCRI",
                "definition": "Highest supplier SCRI in the current weekly digest ranking.",
            },
        ],
        "pillars": [
            {
                "name": "Geographic exposure",
                "features": ["conflict_proximity_score"],
            },
            {
                "name": "Governance stability",
                "features": ["political_stability_index"],
            },
            {
                "name": "Network fragility",
                "features": ["single_source_flag", "dependency_depth"],
            },
            {
                "name": "Operational stress",
                "features": ["port_congestion_score", "weather_risk_score"],
            },
            {
                "name": "Event load",
                "features": ["recent_events_count", "critical_events_count"],
            },
        ],
        "documentation_path": "docs/METRICS.md",
        "limitations_path": "docs/LIMITATIONS.md",
        "model_status": model_status,
    }


@router.get("/methodology")
def get_methodology() -> Dict[str, Any]:
    """Return SCRI methodology for dashboard tooltips and export."""
    return _methodology_payload()


@router.get("/model-status")
def get_model_status() -> Dict[str, Any]:
    """Return risk model deployment status (loaded path, source, calibration)."""
    return get_risk_model_status(ensure_scorer=True)


@router.get("/kpis")
def list_kpi_definitions() -> List[Dict[str, str]]:
    """Return KPI id → definition map."""
    payload = _methodology_payload()
    return payload["kpis"]
