"""Simulation and disruption propagation API routes."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...graph import get_neo4j_client
from ...simulation import DisruptionScenario, propagate_disruption, simulate_disruption
from ...simulation.monte_carlo import MonteCarloSimulator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/simulation", tags=["Simulation"])

DEMO_SCENARIOS: List[dict] = [
    {
        "id": "red-sea-bab-el-mandeb",
        "name": "Red Sea / Bab-el-Mandeb Disruption",
        "description": "Houthi-related shipping attacks force reroutes around Africa, delaying EU–Asia lanes.",
        "source_entity_id": "chokepoint-bab-el-mandeb",
        "source_entity_type": "chokepoint",
        "impact_score": 0.75,
        "event_type": "maritime_attack",
        "severity": 0.8,
        "probability": 0.35,
        "duration_days": 21,
        "region": "Red Sea",
        "sectors": ["shipping", "retail"],
        "mitigations": [
            "Reroute via Cape of Good Hope with +12–18 day buffer",
            "Split bookings across carriers with war-risk coverage",
            "Pre-position safety stock at EU regional DCs",
        ],
    },
    {
        "id": "taiwan-strait-tension",
        "name": "Taiwan Strait Semiconductor Risk",
        "description": "Geopolitical tension elevates risk for advanced chip suppliers and transpacific routes.",
        "source_entity_id": "chokepoint-taiwan-strait",
        "source_entity_type": "chokepoint",
        "impact_score": 0.85,
        "event_type": "geopolitical_tension",
        "severity": 0.9,
        "probability": 0.25,
        "duration_days": 45,
        "region": "Taiwan Strait",
        "sectors": ["semiconductors", "electronics"],
        "mitigations": [
            "Qualify secondary fabs in KR/SG/US CHIPS corridors",
            "Increase die-bank inventory for 90-day cover",
            "Map single-source SKUs to alternate package houses",
        ],
    },
    {
        "id": "suez-canal-blockage",
        "name": "Suez Canal Congestion",
        "description": "Canal slowdown ripples through Mediterranean and Indian Ocean port schedules.",
        "source_entity_id": "chokepoint-suez-canal",
        "source_entity_type": "chokepoint",
        "impact_score": 0.7,
        "event_type": "port_congestion",
        "severity": 0.75,
        "probability": 0.2,
        "duration_days": 14,
        "region": "Suez Canal",
        "sectors": ["manufacturing", "shipping"],
        "mitigations": [
            "Shift urgent air freight for AOG components",
            "Negotiate port priority berths at Piraeus/Jebel Ali",
            "Alert downstream plants with revised ETA windows",
        ],
    },
    {
        "id": "russia-ukraine-supply",
        "name": "Russia–Ukraine Supply Shock",
        "description": "Continued conflict disrupts metals, grain, and eastern EU rail corridors.",
        "source_entity_id": "chokepoint-dover-strait",
        "source_entity_type": "chokepoint",
        "impact_score": 0.88,
        "event_type": "armed_conflict",
        "severity": 0.92,
        "probability": 0.55,
        "duration_days": 60,
        "region": "Eastern Europe",
        "sectors": ["metals", "agriculture", "automotive"],
        "mitigations": [
            "Source steel/aluminum from NAFTA and ASEAN mills",
            "Activate EU border contingency routing via Baltics",
            "Hedge commodity exposure with quarterly forwards",
        ],
    },
    {
        "id": "us-iran-hormuz",
        "name": "US–Iran / Hormuz Escalation",
        "description": "Energy corridor tensions raise tanker premiums and chemical feedstock costs.",
        "source_entity_id": "chokepoint-strait-of-hormuz",
        "source_entity_type": "chokepoint",
        "impact_score": 0.82,
        "event_type": "energy_security",
        "severity": 0.85,
        "probability": 0.3,
        "duration_days": 30,
        "region": "Persian Gulf",
        "sectors": ["energy", "chemicals"],
        "mitigations": [
            "Diversify LNG suppliers away from Gulf concentration",
            "Index surcharge clauses in chemical contracts",
            "Stage diesel backup for critical inland legs",
        ],
    },
    {
        "id": "china-us-trade",
        "name": "China–US Trade Restrictions",
        "description": "Export controls on chips, batteries, and rare earths widen compliance gaps.",
        "source_entity_id": "chokepoint-strait-of-malacca",
        "source_entity_type": "chokepoint",
        "impact_score": 0.74,
        "event_type": "trade_restriction",
        "severity": 0.78,
        "probability": 0.4,
        "duration_days": 90,
        "region": "Transpacific",
        "sectors": ["semiconductors", "ev_batteries"],
        "mitigations": [
            "Reclassify HS codes and audit ECCN exposure",
            "Near-shore assembly to MX/VN for US-bound SKUs",
            "Lock long-term offtake for critical minerals",
        ],
    },
]


class PropagationRequest(BaseModel):
    """BFS propagation request."""

    source_entity_id: str = Field(..., description="Graph entity ID to start from")
    source_entity_type: str = Field(
        default="chokepoint",
        description="Entity type: supplier, port, chokepoint",
    )
    impact_score: float = Field(default=0.7, ge=0.0, le=1.0)


class MonteCarloRequest(BaseModel):
    """Monte Carlo simulation request."""

    event_type: str = "conflict"
    affected_entity_id: str
    entity_type: str = "chokepoint"
    severity: float = Field(default=0.7, ge=0.0, le=1.0)
    probability: float = Field(default=0.3, ge=0.0, le=1.0)
    duration_days: int = Field(default=14, ge=1, le=365)
    iterations: Optional[int] = Field(default=None, ge=1000, le=10000)


def _build_map_overlay(scenario: dict, propagation_dict: dict) -> dict:
    """GeoJSON points/lines for simulation impact on the world map."""
    client = get_neo4j_client()
    source_id = scenario["source_entity_id"]
    affected_ids = propagation_dict.get("affected_suppliers", [])[:25]

    source_rows = client.execute_query(
        """
        MATCH (n)
        WHERE n.id = $id AND n.latitude IS NOT NULL
        RETURN n.id AS id, n.name AS name, n.latitude AS lat, n.longitude AS lon,
               coalesce(n.risk_score, n.current_risk_score, 0.8) AS risk
        LIMIT 1
        """,
        {"id": source_id},
    )

    affected_features = []
    if affected_ids:
        rows = client.execute_query(
            """
            UNWIND $ids AS sid
            MATCH (s:Supplier {id: sid})
            WHERE s.latitude IS NOT NULL
            RETURN s.id AS id, s.name AS name, s.latitude AS lat, s.longitude AS lon,
                   s.risk_score AS risk
            """,
            {"ids": affected_ids},
        )
        for row in rows:
            affected_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                "properties": {
                    "id": row["id"],
                    "name": row["name"],
                    "risk_score": row.get("risk", 0.5),
                    "role": "affected_supplier",
                },
            })

    source_feature = None
    if source_rows:
        row = source_rows[0]
        source_feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            "properties": {
                "id": row["id"],
                "name": row["name"],
                "risk_score": row.get("risk", scenario["severity"]),
                "role": "epicenter",
            },
        }

    return {
        "epicenter": source_feature,
        "affected_suppliers": {"type": "FeatureCollection", "features": affected_features},
        "region": scenario.get("region"),
        "timeline_projection_days": propagation_dict.get("recovery_time_days", 0),
    }


@router.get("/scenarios")
async def list_demo_scenarios() -> dict:
    """Return preset portfolio demo scenarios."""
    return {"scenarios": DEMO_SCENARIOS, "count": len(DEMO_SCENARIOS)}


@router.post("/propagate")
async def run_propagation(body: PropagationRequest) -> dict:
    """Propagate a disruption through the Neo4j knowledge graph (BFS)."""
    try:
        result = propagate_disruption(
            source_entity_id=body.source_entity_id,
            source_entity_type=body.source_entity_type,
            impact_score=body.impact_score,
        )
        return {
            "result": result.to_dict(),
            "path": [step.to_dict() for step in result.propagation_path[:25]],
        }
    except Exception as exc:
        logger.error("propagation_api_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Propagation failed: {exc}",
        ) from exc


@router.post("/monte-carlo")
async def run_monte_carlo(body: MonteCarloRequest) -> dict:
    """Run Monte Carlo disruption simulation (minimum 1000 iterations)."""
    try:
        simulator = MonteCarloSimulator(iterations=body.iterations or 1000)

        scenario = DisruptionScenario(
            event_type=body.event_type,
            affected_entity_id=body.affected_entity_id,
            entity_type=body.entity_type,
            severity=body.severity,
            probability=body.probability,
            duration_days=body.duration_days,
        )
        result = simulator.simulate(scenario)
        return result.to_dict()
    except Exception as exc:
        logger.error("monte_carlo_api_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {exc}",
        ) from exc


@router.post("/scenarios/{scenario_id}/run")
async def run_demo_scenario(scenario_id: str) -> dict:
    """Run BFS propagation + Monte Carlo for a preset scenario with map overlay."""
    scenario = next((s for s in DEMO_SCENARIOS if s["id"] == scenario_id), None)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return _run_scenario_payload(scenario)


class CompareRequest(BaseModel):
    """Side-by-side comparison of two or three preset scenarios."""

    scenario_ids: List[str] = Field(..., min_length=2, max_length=3)


def _run_scenario_payload(scenario: dict) -> dict:
    """Execute propagation + Monte Carlo for a scenario dict."""
    propagation = propagate_disruption(
        source_entity_id=scenario["source_entity_id"],
        source_entity_type=scenario["source_entity_type"],
        impact_score=scenario["impact_score"],
    )

    simulation = simulate_disruption(
        event_type=scenario["event_type"],
        entity_id=scenario["source_entity_id"],
        entity_type=scenario["source_entity_type"],
        severity=scenario["severity"],
        probability=scenario["probability"],
        duration_days=scenario["duration_days"],
    )

    prop_dict = propagation.to_dict()
    mc_dict = simulation.to_dict()

    return {
        "scenario": scenario,
        "propagation": prop_dict,
        "monte_carlo": mc_dict,
        "impact_summary": {
            "headline": f"{prop_dict.get('suppliers_affected', 0)} suppliers exposed in {scenario.get('region', 'region')}",
            "revenue_at_risk_usd": prop_dict.get("revenue_at_risk", 0),
            "disruption_probability": mc_dict.get("disruption_probability", 0),
            "expected_duration_days": mc_dict.get("expected_duration_days", 0),
            "recovery_days": prop_dict.get("recovery_time_days", 0),
        },
        "mitigations": scenario.get("mitigations", []),
        "map_overlay": _build_map_overlay(scenario, prop_dict),
    }


@router.post("/compare")
async def compare_scenarios(body: CompareRequest) -> dict:
    """Compare impact metrics across multiple preset scenarios."""
    comparisons: List[dict] = []
    for scenario_id in body.scenario_ids:
        scenario = next((s for s in DEMO_SCENARIOS if s["id"] == scenario_id), None)
        if scenario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario not found: {scenario_id}",
            )
        payload = _run_scenario_payload(scenario)
        comparisons.append(
            {
                "scenario_id": scenario_id,
                "name": scenario["name"],
                "region": scenario.get("region"),
                "impact_summary": payload["impact_summary"],
                "suppliers_affected": payload["propagation"].get("suppliers_affected", 0),
                "monte_carlo": {
                    "disruption_probability": payload["monte_carlo"].get("disruption_probability"),
                    "expected_duration_days": payload["monte_carlo"].get("expected_duration_days"),
                },
            }
        )

    ranked = sorted(
        comparisons,
        key=lambda c: (
            c["impact_summary"].get("disruption_probability", 0),
            c["suppliers_affected"],
        ),
        reverse=True,
    )

    return {
        "comparisons": comparisons,
        "highest_impact": ranked[0]["scenario_id"] if ranked else None,
        "generated_at": datetime.now().isoformat(),
    }
