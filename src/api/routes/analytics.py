"""Analytics API — sector dashboards, exports, graph health."""

from __future__ import annotations

from datetime import datetime
from typing import List

import structlog
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import PlainTextResponse

from ...graph import get_neo4j_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

SECTOR_KEYWORDS = {
    "semiconductors": ["semiconductor", "electronics", "chip", "taiwan"],
    "energy": ["energy", "oil", "lng", "chemical", "rotterdam"],
    "automotive": ["auto", "motor", "vehicle", "parts"],
    "shipping": ["port", "shipping", "maritime", "logistics"],
}


def _match_sector(name: str, industry: str | None, sector: str) -> bool:
    text = f"{name} {industry or ''}".lower()
    return any(kw in text for kw in SECTOR_KEYWORDS.get(sector, []))


@router.get("/sectors")
async def sector_dashboard() -> dict:
    """Aggregate supplier risk by strategic sector."""
    client = get_neo4j_client()
    rows = client.execute_query(
        """
        MATCH (s:Supplier)
        RETURN s.id AS id, s.name AS name, s.industry AS industry,
               s.country_iso AS country, s.risk_score AS risk, s.critical_flag AS critical
        """
    )
    sectors: dict = {}
    for key in SECTOR_KEYWORDS:
        matched = [r for r in rows if _match_sector(r.get("name", ""), r.get("industry"), key)]
        if not matched:
            sectors[key] = {
                "sector": key,
                "classification_method": "keyword",
                "supplier_count": 0,
                "avg_risk": 0.0,
                "max_risk": 0.0,
                "critical_count": 0,
                "top_suppliers": [],
            }
            continue
        risks = [float(m.get("risk") or 0) for m in matched]
        sectors[key] = {
            "sector": key,
            "classification_method": "keyword",
            "supplier_count": len(matched),
            "avg_risk": round(sum(risks) / len(risks), 3),
            "max_risk": round(max(risks), 3),
            "critical_count": sum(1 for m in matched if m.get("critical")),
            "top_suppliers": sorted(
                [
                    {
                        "id": m["id"],
                        "name": m["name"],
                        "country": m.get("country"),
                        "risk_score": m.get("risk"),
                    }
                    for m in matched
                ],
                key=lambda x: x.get("risk_score") or 0,
                reverse=True,
            )[:5],
        }
    return {"sectors": list(sectors.values()), "generated_at": datetime.now().isoformat(), "classification_method": "keyword"}


@router.get("/export/digest.md")
async def export_digest_markdown() -> PlainTextResponse:
    """Download weekly digest as Markdown executive brief."""
    from ..main import generate_weekly_digest  # noqa: PLC0415

    try:
        digest = await generate_weekly_digest()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    lines: List[str] = [
        "# Meridian Weekly Risk Digest",
        f"*Generated {digest.get('generated_at', datetime.now().isoformat())}*",
        "",
        digest.get("narrative", ""),
        "",
        "## Summary",
        f"- Events (7d): {digest.get('summary', {}).get('total_events', 0)}",
        f"- Affected suppliers: {digest.get('summary', {}).get('affected_suppliers', 0)}",
        "",
        "## Top risks",
    ]
    for r in digest.get("top_risks", [])[:10]:
        lines.append(
            f"- **{r.get('name')}** — {round((r.get('risk_score') or 0) * 100)}% ({r.get('risk_category')})"
        )
    lines.append("")
    lines.append("## Recommendations")
    for rec in digest.get("recommendations", []):
        lines.append(f"- {rec}")

    body = "\n".join(lines)
    return PlainTextResponse(
        content=body,
        headers={"Content-Disposition": "attachment; filename=meridian-weekly-digest.md"},
    )


@router.get("/graph/health")
async def graph_health_report() -> dict:
    """Validate knowledge graph completeness for ops dashboards."""
    client = get_neo4j_client()
    checks = client.execute_query(
        """
        OPTIONAL MATCH (s:Supplier) WITH count(s) AS suppliers
        OPTIONAL MATCH (s2:Supplier) WHERE s2.latitude IS NULL RETURN suppliers,
        count(s2) AS suppliers_missing_geo
        """
    )
    orphans = client.execute_query(
        """
        MATCH (s:Supplier)
        WHERE NOT (s)-[:SHIPS_VIA]->()
        RETURN count(s) AS suppliers_without_ports
        """
    )
    events = client.execute_query("MATCH (e:Event) RETURN count(e) AS event_count")
    linked = client.execute_query(
        """
        MATCH (s:Supplier)
        WHERE (s)<-[:AFFECTS]-(:Event)
        RETURN count(DISTINCT s) AS suppliers_with_events
        """
    )
    tier_edges = client.execute_query(
        """
        MATCH ()-[r:SUPPLIES]->()
        WHERE r.tier >= 2
        RETURN count(r) AS tier2_link_count
        """
    )
    link_confidence = client.execute_query(
        """
        MATCH ()-[r:AFFECTS]->()
        WHERE r.confidence IS NOT NULL
        RETURN avg(r.confidence) AS avg_link_confidence,
               count(r) AS affects_with_confidence
        """
    )
    row = checks[0] if checks else {}
    suppliers = int(row.get("suppliers") or 0)
    missing_geo = int(row.get("suppliers_missing_geo") or 0)
    without_ports = int(orphans[0].get("suppliers_without_ports", 0) if orphans else 0)
    event_count = int(events[0].get("event_count", 0) if events else 0)
    with_events = int(linked[0].get("suppliers_with_events", 0) if linked else 0)
    tier2_count = int(tier_edges[0].get("tier2_link_count", 0) if tier_edges else 0)
    conf_row = link_confidence[0] if link_confidence else {}
    avg_link_confidence = round(float(conf_row.get("avg_link_confidence") or 0.0), 3)
    affects_with_confidence = int(conf_row.get("affects_with_confidence") or 0)

    geo_score = 1.0 - (missing_geo / suppliers) if suppliers else 0.0
    event_score = with_events / suppliers if suppliers else 0.0
    port_score = 1.0 - (without_ports / suppliers) if suppliers else 0.0
    tier_score = min(tier2_count / max(suppliers, 1), 1.0)
    completeness_score = round(
        (geo_score * 0.35) + (event_score * 0.25) + (port_score * 0.25) + (tier_score * 0.15),
        3,
    )

    return {
        "suppliers": suppliers,
        "suppliers_missing_geo": missing_geo,
        "suppliers_with_geo": max(suppliers - missing_geo, 0),
        "suppliers_without_ports": without_ports,
        "suppliers_with_events": with_events,
        "events": event_count,
        "tier2_link_count": tier2_count,
        "avg_link_confidence": avg_link_confidence,
        "affects_with_confidence": affects_with_confidence,
        "link_methods": ["geospatial", "country_match", "demo_seed", "manual"],
        "completeness_score": completeness_score,
        "status": "healthy" if suppliers > 0 else "empty",
    }
