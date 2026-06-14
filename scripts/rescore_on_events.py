#!/usr/bin/env python3
"""Rescore suppliers with recent :AFFECTS links and append TimescaleDB history.

Batch trigger (Phase A) — full Kafka-driven rescore deferred to Phase B.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)


def suppliers_with_recent_affects(neo4j_client, hours: int) -> list[str]:
    """Return supplier IDs linked by new AFFECTS edges in the lookback window."""
    rows = neo4j_client.execute_query(
        """
        MATCH (e:Event)-[r:AFFECTS]->(s:Supplier)
        WHERE coalesce(r.linked_at, e.ingested_at, e.resolved_at)
              > datetime() - duration({hours: $hours})
        RETURN DISTINCT s.id AS supplier_id
        ORDER BY supplier_id
        """,
        {"hours": hours},
    )
    return [str(row["supplier_id"]) for row in rows if row.get("supplier_id")]


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hours",
        type=int,
        default=int(os.getenv("RESCORE_LOOKBACK_HOURS", "24")),
        help="Look back window for new AFFECTS edges (default: 24)",
    )
    args = parser.parse_args()

    from src.graph import get_neo4j_client, get_supplier_repository
    from src.intelligence.feature_builder import build_supplier_features
    from src.intelligence.risk_scorer import get_risk_scorer
    from src.storage.timescale_writer import SupplierScoreRecord, get_timescale_writer

    client = get_neo4j_client()
    repo = get_supplier_repository()
    scorer = get_risk_scorer()
    writer = get_timescale_writer()

    supplier_ids = suppliers_with_recent_affects(client, args.hours)
    if not supplier_ids:
        print(f"No suppliers with :AFFECTS links in last {args.hours}h")
        logger.info("rescore_skipped", reason="no_recent_links", hours=args.hours)
        return 0

    updated = 0
    history_records: list[SupplierScoreRecord] = []

    for supplier_id in supplier_ids:
        supplier = repo.get_by_id(supplier_id)
        if supplier is None:
            continue
        features = build_supplier_features(
            supplier.id,
            single_source_flag=bool(supplier.single_source_flag),
            critical_flag=bool(getattr(supplier, "critical_flag", False)),
            country_iso=supplier.country_iso,
            neo4j_client=client,
        )
        result = scorer.score(supplier.id, "supplier", features)
        client.execute_query(
            """
            MATCH (s:Supplier {id: $id})
            SET s.risk_score = $risk_score,
                s.risk_category = $risk_category,
                s.model_version = $model_version,
                s.scored_at = datetime()
            """,
            {
                "id": supplier.id,
                "risk_score": result.risk_score,
                "risk_category": result.risk_category,
                "model_version": result.model_version,
            },
        )
        history_records.append(
            SupplierScoreRecord(
                supplier_id=supplier.id,
                risk_score=result.risk_score,
                risk_category=result.risk_category,
                model_version=result.model_version,
            )
        )
        updated += 1

    history_written = writer.write_score_batch_sync(history_records) if writer.is_configured() else 0
    print(f"Rescored {updated} suppliers (lookback {args.hours}h)")
    if history_written:
        print(f"TimescaleDB history rows: {history_written}")
    logger.info(
        "rescore_complete",
        suppliers=updated,
        hours=args.hours,
        timescale_rows=history_written,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
