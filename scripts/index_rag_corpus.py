#!/usr/bin/env python3
"""Index Neo4j events, suppliers, scenarios, backtests, and docs into Qdrant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.api.routes.intelligence_extended import BACKTEST_SCENARIOS  # noqa: E402
from src.api.routes.simulation import DEMO_SCENARIOS  # noqa: E402
from src.graph import get_neo4j_client  # noqa: E402
from src.rag.indexing import (  # noqa: E402
    index_backtests,
    index_events,
    index_methodology_docs,
    index_scenarios,
    index_suppliers,
)
from src.rag.qdrant_client import get_qdrant_store  # noqa: E402

logger = structlog.get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-neo4j", action="store_true", help="Index static corpus only")
    args = parser.parse_args()

    store = get_qdrant_store()
    if not store.is_available:
        logger.warning(
            "qdrant_index_skipped",
            message="Qdrant unavailable — exiting 0 for graceful skip",
        )
        return 0

    total = index_methodology_docs()
    total += index_scenarios(DEMO_SCENARIOS)
    total += index_backtests(BACKTEST_SCENARIOS)

    if not args.skip_neo4j:
        try:
            client = get_neo4j_client()
            total += index_events(client)
            total += index_suppliers(client)
        except Exception as exc:
            logger.warning("neo4j_index_partial", error=str(exc))

    logger.info("rag_index_complete", documents=total)
    print(f"Indexed {total} documents into Qdrant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
