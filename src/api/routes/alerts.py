"""Alerts REST endpoints.

Wires the in-memory alert history maintained by ``SlackAlertingService``
to a HTTP API so the frontend ``AlertsView`` can show real data.

Endpoints:
    GET /alerts                 List recent alerts (optionally filter by tier)
    GET /alerts/stats           Service-level alert statistics
    POST /alerts/test           (dev-only) emit a synthetic alert for E2E testing

Future work:
    - Persist alerts to Postgres / Redis (see audit B-13)
    - Add pagination cursor instead of plain limit
    - Add ack/dismiss endpoints
"""

from __future__ import annotations

import os
from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...alerting import get_alerting_service
from ...alerting.slack import Alert, AlertTier

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertResponse(BaseModel):
    """Wire format for an alert (mirrors Alert.to_dict)."""

    tier: str = Field(..., description="info | warning | critical")
    title: str
    message: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    risk_score: Optional[float] = None
    impact_summary: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)
    causal_claim_allowed: Optional[bool] = None
    causal_method: Optional[str] = None
    causal_effect_size: Optional[float] = None
    causal_disclaimer: Optional[str] = None
    causal_sample_count: Optional[int] = None
    timestamp: str


class AlertListResponse(BaseModel):
    """List response wrapper."""

    total: int
    alerts: List[AlertResponse]


def _alert_to_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        tier=alert.tier.value,
        title=alert.title,
        message=alert.message,
        entity_id=alert.entity_id,
        entity_type=alert.entity_type,
        risk_score=alert.risk_score,
        impact_summary=alert.impact_summary,
        recommendations=list(alert.recommendations or []),
        causal_claim_allowed=alert.causal_claim_allowed,
        causal_method=alert.causal_method,
        causal_effect_size=alert.causal_effect_size,
        causal_disclaimer=alert.causal_disclaimer,
        causal_sample_count=alert.causal_sample_count,
        timestamp=alert.timestamp,
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    limit: int = Query(50, ge=1, le=500, description="Max alerts to return"),
    tier: Optional[str] = Query(
        None, description="Filter by tier: info | warning | critical"
    ),
) -> AlertListResponse:
    """Return recent alerts from the alerting service history buffer."""
    service = get_alerting_service()

    tier_enum: Optional[AlertTier] = None
    if tier:
        try:
            tier_enum = AlertTier(tier.lower())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier '{tier}'. Must be one of: "
                + ", ".join(t.value for t in AlertTier),
            ) from exc

    alerts = service.get_recent_alerts(limit=limit, tier=tier_enum)
    return AlertListResponse(
        total=len(alerts),
        alerts=[_alert_to_response(a) for a in alerts],
    )


@router.get("/stats")
async def alert_stats() -> dict:
    """Return alert service statistics."""
    return get_alerting_service().get_stats()


@router.post("/test", status_code=status.HTTP_201_CREATED)
async def emit_test_alert(
    title: str = "Synthetic test alert",
    message: str = "Generated via /alerts/test",
    tier: str = "info",
) -> dict:
    """Emit a test alert. Disabled outside of development."""
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test alert endpoint is disabled in production.",
        )

    try:
        tier_enum = AlertTier(tier.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{tier}'",
        ) from exc

    service = get_alerting_service()
    alert = Alert(tier=tier_enum, title=title, message=message)
    sent = service.send_alert(alert)
    return {"sent": sent, "alert": _alert_to_response(alert).model_dump()}
