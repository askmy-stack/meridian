"""Extended intelligence — copilot, backtests, supplemental map layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...geopolitical.noaa_alerts import weather_alerts_geojson
from ...geopolitical.sanctions_stub import sanctions_geojson
from ...graph import get_neo4j_client
from ...rag.copilot_service import COPILOT_DISCLAIMER, answer_copilot

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

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


class CitationModel(BaseModel):
    source: str
    text: str
    collection: str
    score: Optional[float] = None


class CopilotRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class CopilotResponse(BaseModel):
    answer: str
    suggested_scenario_id: Optional[str] = None
    related_suppliers: List[str] = Field(default_factory=list)
    grounded: bool = True
    disclaimer: str = COPILOT_DISCLAIMER
    graph_facts: List[str] = Field(default_factory=list)
    citations: List[CitationModel] = Field(default_factory=list)
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


@router.post("/copilot", response_model=CopilotResponse)
async def risk_copilot(body: CopilotRequest) -> CopilotResponse:
    """RAG-grounded copilot — retrieves Qdrant corpus + Neo4j facts (D-006)."""
    result = answer_copilot(body.question)
    payload = result.to_dict()
    return CopilotResponse(**payload)


@router.get("/suppliers/{supplier_id}/weak-signals")
async def supplier_weak_signals(supplier_id: str) -> dict:
    """CUSUM changepoint + weak-signal detector for a supplier."""
    from ...intelligence.changepoint import get_supplier_weak_signals

    client = get_neo4j_client()
    return get_supplier_weak_signals(client, supplier_id)


@router.get("/forecast/{supplier_id}")
def supplier_risk_forecast(
    supplier_id: str,
    horizon_days: int = 7,
) -> dict:
    """7/14/30-day risk trajectory (TGN v1 GRU or LSTM fallback)."""
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


@router.get("/regions/{region_id}/regime")
def region_regime(region_id: str, days: int = 30) -> dict:
    """3-state HMM regime (stable / escalation / crisis) for a conflict zone."""
    from ...intelligence.hmm_regime import assess_region_regime

    return assess_region_regime(region_id, days=days).to_dict()


@router.post("/causal/assess")
def assess_causal_link(
    event_severities: List[float],
    supplier_risk_deltas: List[float],
) -> dict:
    """DoWhy causal assessment for event → supplier risk (D-005)."""
    from ...causal.dowhy_engine import assess_event_supplier_link

    return assess_event_supplier_link(event_severities, supplier_risk_deltas).to_dict()
