#!/usr/bin/env python3
"""Ingest ERP/BOM tier edges from CSV into Neo4j.

Creates ``SUPPLIES`` relationships between parent and child suppliers.
Tier depth is stored on the relationship for graph completeness scoring.

Usage:
    python scripts/ingest_erp_csv.py --file data/sample_erp_tiers.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph.client import Neo4jClient

logger = structlog.get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest ERP tier edges into Neo4j")
    parser.add_argument(
        "--file",
        default="data/sample_erp_tiers.csv",
        help="CSV with parent_supplier_id, child_supplier_id, tier",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without writing to Neo4j",
    )
    return parser.parse_args()


def read_erp_csv(filepath: str) -> List[Dict[str, str]]:
    """Read ERP tier rows from CSV."""
    rows: List[Dict[str, str]] = []
    with open(filepath, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("parent_supplier_id") and row.get("child_supplier_id"):
                rows.append(row)
    return rows


def ingest_tier_edges(client: Neo4jClient, rows: List[Dict[str, str]], *, dry_run: bool) -> int:
    """Create SUPPLIES relationships with tier metadata."""
    created = 0
    for row in rows:
        parent_id = row["parent_supplier_id"].strip()
        child_id = row["child_supplier_id"].strip()
        tier = int(row.get("tier") or 2)
        notes = row.get("notes", "")

        if dry_run:
            print(f"Would link {parent_id} -[:SUPPLIES {{tier:{tier}}}]-> {child_id}")
            created += 1
            continue

        client.execute_query(
            """
            MERGE (parent:Supplier {id: $parent_id})
            ON CREATE SET parent.name = $parent_id, parent.country_iso = 'XX'
            MERGE (child:Supplier {id: $child_id})
            ON CREATE SET child.name = $child_id, child.country_iso = 'XX'
            MERGE (parent)-[r:SUPPLIES]->(child)
            SET r.tier = $tier,
                r.source = 'erp_csv',
                r.notes = $notes,
                r.updated_at = datetime()
            """,
            {
                "parent_id": parent_id,
                "child_id": child_id,
                "tier": tier,
                "notes": notes,
            },
        )
        created += 1

    logger.info("erp_tier_edges_ingested", count=created, dry_run=dry_run)
    return created


def main() -> int:
    load_dotenv()
    args = parse_args()
    rows = read_erp_csv(args.file)
    if not rows:
        print(f"No rows found in {args.file}")
        return 1

    if args.dry_run:
        ingest_tier_edges(Neo4jClient(), rows, dry_run=True)
        return 0

    from src.graph import get_neo4j_client

    client = get_neo4j_client()
    count = ingest_tier_edges(client, rows, dry_run=False)
    print(f"Ingested {count} SUPPLIES tier edges from {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
