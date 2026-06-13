"""Build FeatureVector instances from Neo4j supplier context."""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from .risk_scorer import FeatureVector

logger = structlog.get_logger(__name__)

# Country-level political stability proxy (World Bank WGI-inspired scale, demo values)
# Higher = more stable. Sources documented in docs/METRICS.md
COUNTRY_STABILITY: Dict[str, float] = {
    "CN": 0.55,
    "TW": 0.62,
    "KR": 0.78,
    "JP": 0.88,
    "IN": 0.58,
    "AE": 0.72,
    "TR": 0.48,
    "NL": 0.92,
    "DE": 0.90,
    "PL": 0.75,
    "SG": 0.91,
    "VN": 0.60,
    "TH": 0.65,
    "PH": 0.52,
    "ID": 0.57,
    "AU": 0.89,
    "BR": 0.50,
    "MX": 0.54,
    "CA": 0.93,
    "US": 0.85,
    "IL": 0.45,
    "EG": 0.42,
    "ZA": 0.48,
}


def build_supplier_features(
    supplier_id: str,
    *,
    single_source_flag: bool = False,
    critical_flag: bool = False,
    country_iso: Optional[str] = None,
    neo4j_client: Optional[Any] = None,
) -> FeatureVector:
    """Assemble features for a supplier from graph signals and static proxies."""
    recent_events = 0
    critical_events = 0
    conflict_proximity = 0.1
    port_congestion = 0.0

    if neo4j_client is not None:
        try:
            rows = neo4j_client.execute_query(
                """
                MATCH (s:Supplier {id: $supplier_id})
                OPTIONAL MATCH (e:Event)-[:AFFECTS]->(s)
                WHERE e.ingested_at > datetime() - duration('P30D')
                WITH s,
                     count(e) AS recent,
                     sum(CASE WHEN e.severity >= 0.75 THEN 1 ELSE 0 END) AS critical,
                     max(e.severity) AS max_severity
                OPTIONAL MATCH (s)-[:SHIPS_VIA]->(p:Port)-[:PASSES_THROUGH]->(c:Chokepoint)
                RETURN recent, critical, max_severity, coalesce(c.vessel_count, 0) AS vessels
                LIMIT 1
                """,
                {"supplier_id": supplier_id},
            )
            if rows:
                row = rows[0]
                recent_events = int(row.get("recent") or 0)
                critical_events = int(row.get("critical") or 0)
                max_sev = row.get("max_severity")
                if max_sev is not None:
                    conflict_proximity = min(float(max_sev), 1.0)
                vessels = int(row.get("vessels") or 0)
                port_congestion = min(vessels / 20.0, 1.0)
        except Exception as exc:
            logger.warning("feature_query_failed", supplier_id=supplier_id, error=str(exc))

    if critical_flag and critical_events == 0:
        critical_events = 1

    stability = COUNTRY_STABILITY.get((country_iso or "").upper(), 0.5)

    return FeatureVector(
        conflict_proximity_score=conflict_proximity,
        political_stability_index=stability,
        port_congestion_score=port_congestion,
        recent_events_count=recent_events,
        critical_events_count=critical_events,
        single_source_flag=single_source_flag,
        supplier_financial_health=0.35 if critical_flag else 0.65,
    )
