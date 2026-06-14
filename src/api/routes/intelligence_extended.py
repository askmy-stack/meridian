"""Extended intelligence — copilot, backtests, supplemental map layers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...geopolitical.noaa_alerts import weather_alerts_geojson
from ...geopolitical.sanctions_stub import sanctions_geojson
from ...graph import get_neo4j_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

COPILOT_DISCLAIMER = (
    "Template copilot — answers use Neo4j graph facts and keyword routing only. "
    "Not a general LLM. Unverified questions receive an explicit uncertainty response."
)

SCENARIO_KEYWORDS = {
    "red-sea-bab-el-mandeb": ("red sea", "houthi", "bab"),
    "taiwan-strait-tension": ("taiwan", "semiconductor", "chip"),
    "suez-canal-blockage": ("suez", "canal"),
    "russia-ukraine-supply": ("ukraine", "russia"),
    "us-iran-hormuz": ("hormuz", "iran"),
    "china-us-trade": ("china", "tariff", "export control"),
}

BACKTEST_SCENARIOS = {
    "suez-2021": {
        "title": "Ever Given — Suez Canal blockage (Mar 2021)",
        "description": "6-day canal closure; $9.6B daily trade delay; Asia-EU lead times +7-14 days.",
        "region": "Suez Canal",
        "latitude": 30.0,
        "longitude": 32.35,
        "severity": 0.88,
        "lessons": [
            "Dual-route contracts (Suez + Cape) reduced single-point failure.",
            "Container rollover surcharges peaked 3 weeks post-incident.",
        ],
    },
    "ukraine-2022": {
        "title": "Russia invasion of Ukraine (Feb 2022)",
        "description": "Grain, metals, and rail corridors disrupted; EU energy repricing.",
        "region": "Eastern Europe",
        "latitude": 49.0,
        "longitude": 31.5,
        "severity": 0.95,
        "lessons": [
            "Eastern EU suppliers needed alternate steel sourcing within 45 days.",
            "Energy-intensive SKUs saw 18-32% COGS spike in Q2 2022.",
        ],
    },
}


class CopilotRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class CopilotResponse(BaseModel):
    answer: str
    suggested_scenario_id: Optional[str] = None
    related_suppliers: List[str] = Field(default_factory=list)
    grounded: bool = True
    disclaimer: str = COPILOT_DISCLAIMER
    graph_facts: List[str] = Field(default_factory=list)
    generated_at: str


@router.get("/layers/weather")
async def weather_layer() -> dict:
    return weather_alerts_geojson()


@router.get("/layers/sanctions")
async def sanctions_layer() -> dict:
    return sanctions_geojson()


@router.get("/backtest/{scenario_id}")
async def historical_backtest(scenario_id: str) -> dict:
    """Replay a historical disruption against the current supplier graph."""
    preset = BACKTEST_SCENARIOS.get(scenario_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Backtest scenario not found")

    client = get_neo4j_client()
    affected = client.execute_query(
        """
        MATCH (s:Supplier)
        WHERE s.risk_score >= 0.5
        RETURN s.id AS id, s.name AS name, s.risk_score AS risk,
               s.latitude AS lat, s.longitude AS lon
        ORDER BY s.risk_score DESC
        LIMIT 15
        """
    )
    return {
        "backtest": preset,
        "scenario_id": scenario_id,
        "would_affect_today": len(affected),
        "suppliers": affected,
        "generated_at": datetime.now().isoformat(),
    }


def _graph_context(client: Any) -> Tuple[List[str], List[str], List[str]]:
    """Return high-risk supplier names, graph facts, and fact strings for grounding."""
    suppliers = client.execute_query(
        """
        MATCH (s:Supplier)
        WHERE s.risk_score >= 0.7
        RETURN s.name AS name, s.risk_score AS risk
        ORDER BY s.risk_score DESC
        LIMIT 5
        """
    )
    stats = client.execute_query(
        """
        OPTIONAL MATCH (s:Supplier) WITH count(s) AS suppliers
        OPTIONAL MATCH (e:Event) WITH suppliers, count(e) AS events
        OPTIONAL MATCH (s2:Supplier)<-[:AFFECTS]-(:Event) WITH suppliers, events,
             count(DISTINCT s2) AS affected
        RETURN suppliers, events, affected
        """
    )
    row = stats[0] if stats else {}
    names = [r["name"] for r in suppliers]
    facts = [
        f"{row.get('suppliers', 0)} suppliers in graph",
        f"{row.get('events', 0)} events materialized",
        f"{row.get('affected', 0)} suppliers linked to events",
    ]
    return names, facts, facts


def _match_scenario(question: str) -> Optional[str]:
    q = question.lower()
    for scenario_id, keywords in SCENARIO_KEYWORDS.items():
        if any(word in q for word in keywords):
            return scenario_id
    return None


@router.post("/copilot", response_model=CopilotResponse)
async def risk_copilot(body: CopilotRequest) -> CopilotResponse:
    """Graph-grounded template copilot — no unconstrained LLM generation."""
    client = get_neo4j_client()
    names, graph_facts, _ = _graph_context(client)
    scenario_id = _match_scenario(body.question)

    if scenario_id:
        answer = (
            f"Based on graph data ({', '.join(graph_facts)}), I recommend the "
            f"{scenario_id.replace('-', ' ')} simulator preset. "
            f"Top exposed suppliers: {', '.join(names) if names else 'none seeded'}."
        )
        grounded = True
    elif names:
        answer = (
            "I don't have a matching scenario preset for that question. "
            f"Graph facts: {', '.join(graph_facts)}. "
            f"Current high-risk suppliers: {', '.join(names)}. "
            "Try Red Sea, Taiwan semiconductors, Suez, or Ukraine supply shocks."
        )
        grounded = False
    else:
        answer = (
            "I don't know — the graph has no seeded suppliers yet. "
            "Run make seed-all, then ask about a supported scenario keyword."
        )
        grounded = False

    answer = re.sub(r"\*\*", "", answer)

    return CopilotResponse(
        answer=answer,
        suggested_scenario_id=scenario_id,
        related_suppliers=names,
        grounded=grounded,
        disclaimer=COPILOT_DISCLAIMER,
        graph_facts=graph_facts,
        generated_at=datetime.now().isoformat(),
    )


@router.get("/forecast/{supplier_id}")
def supplier_risk_forecast(
    supplier_id: str,
    horizon_days: int = 7,
) -> dict:
    """7/14/30-day risk trajectory (TGN stub with LSTM fallback)."""
    from ...forecasting.tgn_forecaster import get_tgn_forecaster

    forecaster = get_tgn_forecaster()
    forecast = forecaster.predict(
        entity_id=supplier_id,
        entity_type="supplier",
        horizon_days=horizon_days,
    )
    payload = forecast.to_dict()
    payload["model"] = "tgn" if forecaster.is_available() else "lstm_fallback"
    payload["methodology"] = "docs/METRICS.md#forecasting-tgn--research-track"
    return payload


@router.post("/causal/assess")
def assess_causal_link(
    event_severities: List[float],
    supplier_risk_deltas: List[float],
) -> dict:
    """DoWhy causal assessment for event → supplier risk (D-005)."""
    from ...causal.dowhy_engine import assess_event_supplier_link

    return assess_event_supplier_link(event_severities, supplier_risk_deltas).to_dict()
