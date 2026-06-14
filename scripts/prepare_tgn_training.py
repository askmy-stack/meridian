#!/usr/bin/env python3
"""Validate supplier snapshot exports and emit a TGN training readiness manifest."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from dotenv import load_dotenv

logger = structlog.get_logger(__name__)

SNAPSHOT_PATTERN = re.compile(r"^supplier_snapshot_(\d{8})\.csv$")
MIN_SNAPSHOTS_FOR_READY = 7


@dataclass
class SnapshotInfo:
    """Metadata for a single supplier snapshot CSV."""

    path: Path
    date_stamp: str
    row_count: int


def snapshot_dir() -> Path:
    """Return the directory containing supplier snapshot CSV exports."""
    return Path(os.getenv("SNAPSHOT_DIR", "data/snapshots"))


def discover_snapshots(directory: Path) -> List[SnapshotInfo]:
    """Find and summarize all supplier_snapshot_*.csv files in *directory*."""
    snapshots: List[SnapshotInfo] = []
    if not directory.is_dir():
        return snapshots

    for path in sorted(directory.glob("supplier_snapshot_*.csv")):
        match = SNAPSHOT_PATTERN.match(path.name)
        if not match:
            logger.warning("snapshot_skipped", path=str(path), reason="unexpected_filename")
            continue

        row_count = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
        snapshots.append(
            SnapshotInfo(path=path, date_stamp=match.group(1), row_count=row_count)
        )

    snapshots.sort(key=lambda item: item.date_stamp)
    return snapshots


def fetch_graph_edge_counts() -> Dict[str, Any]:
    """Optional Neo4j edge counts for training manifest (graceful when unavailable)."""
    try:
        from src.graph import get_neo4j_client

        client = get_neo4j_client()
        rows = client.execute_query(
            """
            OPTIONAL MATCH ()-[a:AFFECTS]->() WITH count(a) AS affects_edges
            OPTIONAL MATCH ()-[s:SUPPLIES]->() WITH affects_edges, count(s) AS supplies_edges
            OPTIONAL MATCH (sup:Supplier) WITH affects_edges, supplies_edges, count(sup) AS suppliers
            RETURN affects_edges, supplies_edges, suppliers
            """
        )
        row = rows[0] if rows else {}
        return {
            "affects_edges": int(row.get("affects_edges") or 0),
            "supplies_edges": int(row.get("supplies_edges") or 0),
            "supplier_nodes": int(row.get("suppliers") or 0),
            "source": "neo4j",
        }
    except Exception as exc:
        logger.warning("graph_edge_counts_unavailable", error=str(exc))
        return {
            "affects_edges": 0,
            "supplies_edges": 0,
            "supplier_nodes": 0,
            "source": "unavailable",
        }


def build_manifest(
    snapshots: List[SnapshotInfo],
    *,
    min_ready: int = MIN_SNAPSHOTS_FOR_READY,
    graph_edges: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build manifest JSON describing snapshot coverage and training readiness."""
    dates = [item.date_stamp for item in snapshots]
    edge_info = graph_edges if graph_edges is not None else fetch_graph_edge_counts()
    total_rows = sum(item.row_count for item in snapshots)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "snapshot_dir": str(snapshot_dir()),
        "snapshot_count": len(snapshots),
        "total_supplier_rows": total_rows,
        "date_range": {
            "earliest": dates[0] if dates else None,
            "latest": dates[-1] if dates else None,
        },
        "snapshots": [
            {
                "file": item.path.name,
                "date": item.date_stamp,
                "row_count": item.row_count,
            }
            for item in snapshots
        ],
        "graph_edges": edge_info,
        "min_snapshots_for_ready": min_ready,
        "ready_for_training": len(snapshots) >= min_ready,
        "training_command": "python scripts/train_tgn_v1.py",
        "next_steps": [
            "Run scripts/export_graph_snapshots.py daily (cron or pipeline)",
            "Re-run this script until ready_for_training is true",
            "Train TGN v1 GRU: python scripts/train_tgn_v1.py (see docs/TGN_RESEARCH.md)",
        ],
    }


def write_manifest(manifest: Dict[str, Any], output_path: Path) -> None:
    """Persist manifest JSON to *output_path*."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    logger.info(
        "tgn_manifest_written",
        path=str(output_path),
        snapshot_count=manifest["snapshot_count"],
        ready=manifest["ready_for_training"],
    )


def main() -> int:
    """CLI entry point."""
    load_dotenv()
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )

    directory = snapshot_dir()
    snapshots = discover_snapshots(directory)

    if not snapshots:
        logger.warning(
            "no_snapshots_found",
            directory=str(directory),
            hint="Run scripts/export_graph_snapshots.py after Neo4j is populated",
        )

    manifest = build_manifest(snapshots)
    output_path = directory / "tgn_manifest.json"
    write_manifest(manifest, output_path)

    if not manifest["ready_for_training"]:
        logger.info(
            "tgn_not_ready",
            have=manifest["snapshot_count"],
            need=manifest["min_snapshots_for_ready"],
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
