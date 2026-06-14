"""Build FeatureVector instances from Neo4j supplier context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import structlog

from .feature_vector import FeatureVector

logger = structlog.get_logger(__name__)

FEATURE_COUNT = 13
REPO_ROOT = Path(__file__).resolve().parents[2]
WGI_CACHE_PATH = REPO_ROOT / "data" / "wgi_stability.json"

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


def _load_wgi_cache() -> Tuple[Dict[str, float], Dict[str, str]]:
    """Load cached WGI scores and per-country provenance."""
    if not WGI_CACHE_PATH.is_file():
        return COUNTRY_STABILITY, {iso: "static_fallback" for iso in COUNTRY_STABILITY}

    try:
        payload = json.loads(WGI_CACHE_PATH.read_text(encoding="utf-8"))
        scores = payload.get("scores") or {}
        sources = payload.get("sources") or {}
        merged_scores = {**COUNTRY_STABILITY, **{k.upper(): float(v) for k, v in scores.items()}}
        merged_sources = {iso: "static_fallback" for iso in COUNTRY_STABILITY}
        for iso, source in sources.items():
            merged_sources[iso.upper()] = str(source)
        return merged_scores, merged_sources
    except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        logger.warning("wgi_cache_load_failed", error=str(exc))
        return COUNTRY_STABILITY, {iso: "static_fallback" for iso in COUNTRY_STABILITY}


def political_stability_for_country(country_iso: Optional[str]) -> Tuple[float, str]:
    """Return stability score and provenance token for a country ISO code."""
    scores, sources = _load_wgi_cache()
    country_key = (country_iso or "").upper()
    score = scores.get(country_key, 0.5)
    source = sources.get(country_key, "static_fallback")
    return score, source


def _query_graph_signals(
    supplier_id: str,
    neo4j_client: Any,
) -> Tuple[int, int, float, float, bool]:
    """Return recent/critical events, conflict proximity, port congestion, query_ok."""
    recent_events = 0
    critical_events = 0
    conflict_proximity = 0.1
    port_congestion = 0.0
    query_ok = False

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
        query_ok = True
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

    return recent_events, critical_events, conflict_proximity, port_congestion, query_ok


def _weather_risk_from_noaa(country_iso: Optional[str]) -> float:
    """Derive weather risk from NOAA demo alerts matched by supplier country ports."""
    from ..geopolitical.noaa_alerts import WEATHER_ALERTS

    country_ports: Dict[str, list] = {
        "US": ["USHOU", "USMSY"],
        "EG": ["EGPSD"],
        "GR": ["GRPIR"],
    }
    ports = country_ports.get((country_iso or "").upper(), [])
    if not ports:
        return 0.0

    severities = [
        float(alert["severity"])
        for alert in WEATHER_ALERTS
        if any(port in alert.get("affected_ports", []) for port in ports)
    ]
    return max(severities) if severities else 0.0


def _sanctions_exposure(country_iso: Optional[str]) -> float:
    """OpenSanctions-style exposure score from demo stub entities."""
    from ..geopolitical.sanctions_stub import SANCTIONED_ENTITIES

    country = (country_iso or "").upper()
    if not country:
        return 0.0
    matches = [float(e["severity"]) for e in SANCTIONED_ENTITIES if e.get("country") == country]
    return max(matches) if matches else 0.0


def compute_pillar_scores(features: FeatureVector) -> Dict[str, float]:
    """Decompose SCRI features into four weighted pillar indices (not separate ML models)."""
    geographic = min(
        1.0,
        (features.conflict_proximity_score + (1.0 - features.political_stability_index)) / 2.0,
    )
    operational = min(
        1.0,
        (features.port_congestion_score + features.weather_risk_score) / 2.0,
    )
    network = min(
        1.0,
        (float(features.single_source_flag) + min(features.dependency_depth / 5.0, 1.0)) / 2.0,
    )
    event_load = min(
        1.0,
        (
            min(features.recent_events_count / 10.0, 1.0)
            + min(features.critical_events_count / 5.0, 1.0)
        )
        / 2.0,
    )
    return {
        "geographic": round(geographic, 3),
        "operational": round(operational, 3),
        "network": round(network, 3),
        "event_load": round(event_load, 3),
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
        recent_events, critical_events, conflict_proximity, port_congestion, _ = (
            _query_graph_signals(supplier_id, neo4j_client)
        )

    if critical_flag and critical_events == 0:
        critical_events = 1

    weather_risk = _weather_risk_from_noaa(country_iso)
    sanctions = _sanctions_exposure(country_iso)
    conflict_proximity = max(conflict_proximity, sanctions * 0.6)

    stability, stability_source = political_stability_for_country(country_iso)
    logger.debug(
        "wgi_provenance",
        supplier_id=supplier_id,
        country_iso=country_iso,
        source=stability_source,
    )

    return FeatureVector(
        conflict_proximity_score=conflict_proximity,
        political_stability_index=stability,
        port_congestion_score=port_congestion,
        weather_risk_score=weather_risk,
        recent_events_count=recent_events,
        critical_events_count=critical_events,
        single_source_flag=single_source_flag,
        supplier_financial_health=0.35 if critical_flag else 0.65,
    )


def build_feature_provenance(
    supplier_id: str,
    *,
    single_source_flag: bool = False,
    critical_flag: bool = False,
    country_iso: Optional[str] = None,
    neo4j_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Document which SCRI features are live vs static/default for UI transparency."""
    recent_events = 0
    critical_events = 0
    conflict_proximity = 0.1
    port_congestion = 0.0
    graph_queried = False
    graph_live = False

    if neo4j_client is not None:
        recent_events, critical_events, conflict_proximity, port_congestion, graph_queried = (
            _query_graph_signals(supplier_id, neo4j_client)
        )
        graph_live = graph_queried and (
            recent_events > 0 or critical_events > 0 or port_congestion > 0
        )

    country_key = (country_iso or "").upper()
    _, stability_source = political_stability_for_country(country_iso)
    weather_risk = _weather_risk_from_noaa(country_iso)
    sanctions = _sanctions_exposure(country_iso)

    features: Dict[str, Dict[str, str]] = {
        "conflict_proximity_score": {
            "source": "live_graph" if graph_live and conflict_proximity > 0.1 else "default",
            "note": "Event severity max in 30d window" if graph_live else "Baseline 0.1",
        },
        "political_stability_index": {
            "source": stability_source,
            "note": (
                f"WGI cache ({country_key})"
                if stability_source == "live_wgi"
                else f"Static table ({country_key or 'unknown'})"
            ),
        },
        "port_congestion_score": {
            "source": "live_graph" if graph_live and port_congestion > 0 else "default",
            "note": "Chokepoint vessel counts" if port_congestion > 0 else "No congestion signal",
        },
        "weather_risk_score": {
            "source": "noaa_demo" if weather_risk > 0 else "default_zero",
            "note": "NOAA alert severity matched by country ports" if weather_risk > 0 else "No weather alert match",
        },
        "sanctions_exposure": {
            "source": "opensanctions_stub" if sanctions > 0 else "default_zero",
            "note": f"Country sanctions stub ({country_key})" if sanctions > 0 else "No sanctions match",
        },
        "recent_events_count": {
            "source": "live_graph" if graph_queried and recent_events > 0 else "default",
            "note": f"{recent_events} events in 30d" if graph_queried else "Graph unavailable",
        },
        "critical_events_count": {
            "source": "live_graph"
            if graph_queried and (critical_events > 0 or critical_flag)
            else "default",
            "note": "Severity ≥ 0.75 events or critical supplier flag",
        },
        "dependency_depth": {
            "source": "default",
            "note": "Tier depth not ingested — defaults to tier 1",
        },
        "single_source_flag": {
            "source": "supplier_record",
            "note": "Neo4j Supplier.single_source_flag",
        },
        "alternative_sources_count": {
            "source": "default_zero",
            "note": "Alternate supplier count not computed in MVP",
        },
        "supplier_financial_health": {
            "source": "heuristic",
            "note": "Derived from critical_flag — not ERP financials",
        },
        "market_volatility_index": {
            "source": "default_zero",
            "note": "Market feed not connected",
        },
        "historical_disruption_count": {
            "source": "default_zero",
            "note": "12-month history not materialized",
        },
        "avg_resolution_time_days": {
            "source": "default_zero",
            "note": "Resolution time not tracked in graph",
        },
    }

    live_sources = {"live_graph", "supplier_record", "noaa_demo", "opensanctions_stub", "live_wgi"}
    live_count = sum(1 for meta in features.values() if meta["source"] in live_sources)

    return {
        "features": features,
        "live_feature_count": live_count,
        "total_features": FEATURE_COUNT,
        "summary": f"{live_count}/{FEATURE_COUNT} features from live graph",
    }
