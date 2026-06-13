#!/usr/bin/env python3
"""Export daily graph snapshots for TGN training."""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)


def main() -> int:
    load_dotenv()
    out_dir = Path(os.getenv("SNAPSHOT_DIR", "data/snapshots"))
    out_dir.mkdir(parents=True, exist_ok=True)

    from src.graph import get_neo4j_client

    client = get_neo4j_client()
    rows = client.execute_query(
        """
        MATCH (s:Supplier)
        OPTIONAL MATCH (e:Event)-[:AFFECTS]->(s)
        WHERE e.ingested_at > datetime() - duration('P30D')
        WITH s, count(e) AS events, max(e.severity) AS max_severity
        RETURN s.id AS supplier_id, s.name AS name, s.risk_score AS risk_score,
               events, max_severity
        ORDER BY s.name
        """
    )

    stamp = datetime.utcnow().strftime("%Y%m%d")
    path = out_dir / f"supplier_snapshot_{stamp}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["supplier_id", "name", "risk_score", "events", "max_severity"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "supplier_id": row.get("supplier_id"),
                    "name": row.get("name"),
                    "risk_score": row.get("risk_score"),
                    "events": row.get("events", 0),
                    "max_severity": row.get("max_severity"),
                }
            )

    print(f"Wrote {len(rows)} rows to {path}")
    logger.info("snapshot_exported", path=str(path), rows=len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
