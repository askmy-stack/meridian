#!/usr/bin/env python3
"""Export Event→Supplier causal pairs to CSV for offline DoWhy analysis."""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.causal.pipeline_alerts import causal_pair_limit, fetch_event_supplier_pairs

logger = structlog.get_logger(__name__)


def output_path() -> Path:
    return Path(os.getenv("CAUSAL_PAIRS_CSV", "data/causal/event_supplier_pairs.csv"))


def fetch_detailed_pairs(client: Any, limit: int) -> list[dict]:
    """Fetch paired events and suppliers with identifiers for offline analysis."""
    rows = client.execute_query(
        """
        MATCH (e:Event)-[r:AFFECTS]->(s:Supplier)
        WHERE e.severity IS NOT NULL AND s.risk_score IS NOT NULL
        RETURN e.id AS event_id,
               e.event_type AS event_type,
               e.severity AS event_severity,
               e.ingested_at AS ingested_at,
               s.id AS supplier_id,
               s.name AS supplier_name,
               s.risk_score AS supplier_risk_score,
               r.confidence AS link_confidence
        ORDER BY e.ingested_at DESC
        LIMIT $limit
        """,
        {"limit": limit},
    )
    return rows


def main() -> int:
    load_dotenv()
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )

    limit = causal_pair_limit()
    out = output_path()
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from src.graph import get_neo4j_client

        client = get_neo4j_client()
        rows = fetch_detailed_pairs(client, limit)
        severities, risks = fetch_event_supplier_pairs(client, limit=limit)
    except Exception as exc:
        logger.error("causal_pairs_export_failed", error=str(exc))
        print(f"Neo4j unavailable — cannot export causal pairs: {exc}", file=sys.stderr)
        return 1

    fieldnames = [
        "event_id",
        "event_type",
        "event_severity",
        "ingested_at",
        "supplier_id",
        "supplier_name",
        "supplier_risk_score",
        "link_confidence",
    ]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})

    summary_path = out.with_suffix(".summary.json")
    summary_path.write_text(
        (
            '{"exported_at":"'
            + datetime.utcnow().isoformat()
            + 'Z","pair_count":'
            + str(len(rows))
            + ',"correlation_pairs":'
            + str(min(len(severities), len(risks)))
            + "}"
        ),
        encoding="utf-8",
    )

    logger.info("causal_pairs_exported", path=str(out), rows=len(rows))
    print(f"Wrote {len(rows)} causal pairs to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
