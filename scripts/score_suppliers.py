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


def main() -> int:
    load_dotenv()
    from src.graph import get_neo4j_client, get_supplier_repository
    from src.intelligence.feature_builder import build_supplier_features
    from src.intelligence.risk_scorer import get_risk_scorer

    client = get_neo4j_client()
    repo = get_supplier_repository()
    scorer = get_risk_scorer()

    suppliers = repo.get_all(limit=500)
    updated = 0

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
        updated += 1

    print(f"Scored {updated} suppliers (model: {scorer.model_path or 'default'})")
    logger.info("suppliers_scored", count=updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
