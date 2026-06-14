#!/usr/bin/env python3
"""Batch pipeline wrapper — portfolio demo without Kafka."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import structlog
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger(__name__)


def main() -> int:
    load_dotenv()
    mode = os.getenv("PIPELINE_MODE", "batch")
    root = Path(__file__).parent.parent
    py = sys.executable

    if mode != "batch":
        logger.info("pipeline_batch_delegating_to_kafka", mode=mode)
        return subprocess.call([py, str(root / "scripts/pipeline_refresh.py")])

    logger.info("pipeline_batch_mode", message="Skipping Kafka — direct Neo4j refresh")
    print("PIPELINE_MODE=batch — skipping Kafka producers and consumers")

    steps = [
        ([py, str(root / "scripts/seed_demo_scenarios.py")], "demo scenarios"),
        ([py, str(root / "scripts/score_suppliers.py")], "supplier scoring"),
    ]

    for cmd, label in steps:
        print(f"Running {label}…")
        rc = subprocess.call(cmd)
        if rc != 0:
            logger.warning("pipeline_batch_step_failed", step=label, exit_code=rc)
            return rc

    print("Batch pipeline complete — see docs/ARCHITECTURE_DEMO.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
