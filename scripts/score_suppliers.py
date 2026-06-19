#!/usr/bin/env python3
"""Score all suppliers with trained XGBoost model and persist to Neo4j."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)


def _persist_scores_to_timescale(
    records: list,
) -> int:
    """Append score history batch; skip silently when TimescaleDB is down."""
    from src.storage.timescale_writer import SupplierScoreRecord, get_timescale_writer

    writer = get_timescale_writer()
    if not writer.is_configured():
        logger.info("timescale_history_skipped", reason="not_configured")
        return 0
    return writer.write_score_batch_sync(records)


def main() -> int:
    load_dotenv()
    from src.graph import get_neo4j_client, get_supplier_repository
    from src.intelligence.feature_builder import build_supplier_features
    from src.intelligence.risk_scorer import get_risk_scorer
    from src.storage.timescale_writer import SupplierScoreRecord

    client = get_neo4j_client()
    repo = get_supplier_repository()
    scorer = get_risk_scorer()

    suppliers = repo.get_all(limit=500)
    updated = 0
    history_records: list[SupplierScoreRecord] = []

    for supplier in suppliers:
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
                feature_snapshot=features.to_dict() if hasattr(features, "to_dict") else None,
            )
        )
        updated += 1

    history_written = _persist_scores_to_timescale(history_records)

    try:
        from src.rag.indexing import index_suppliers as rag_index_suppliers
        from src.rag.qdrant_client import get_qdrant_store

        if get_qdrant_store().is_available:
            rag_index_suppliers(client)
            logger.info("rag_suppliers_reindexed_after_score")
    except Exception as exc:
        logger.warning("rag_suppliers_reindex_skipped", error=str(exc))

    print(f"Scored {updated} suppliers (model: {scorer.model_path or 'default'})")
    if history_written:
        print(f"TimescaleDB history rows: {history_written}")
    logger.info("suppliers_scored", count=updated, timescale_rows=history_written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
