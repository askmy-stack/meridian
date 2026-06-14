#!/usr/bin/env python3
"""Validate that all required environment variables are set before starting Meridian.

Usage:
    python scripts/validate_env.py             # validates current shell env
    python scripts/validate_env.py --strict    # fails if any optional var is missing
    python scripts/validate_env.py --env-file .env

Exit codes:
    0  all required vars present
    1  one or more required vars missing
    2  invalid CLI usage
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class EnvVar:
    name: str
    required: bool
    description: str
    only_when_env: Optional[str] = None  # only required when ENVIRONMENT == this value


# --- Manifest ---------------------------------------------------------------
REQUIRED_VARS: List[EnvVar] = [
    EnvVar("KAFKA_BOOTSTRAP_SERVERS", True, "Kafka broker bootstrap servers"),
    EnvVar("NEO4J_URI", True, "Neo4j Bolt URI (bolt://host:port)"),
    EnvVar("NEO4J_USER", True, "Neo4j username"),
    EnvVar("NEO4J_PASSWORD", True, "Neo4j password"),
    EnvVar("JWT_SECRET_KEY", True, "JWT signing secret", only_when_env="production"),
    EnvVar(
        "MERIDIAN_ADMIN_PASSWORD",
        True,
        "Bootstrap admin password",
        only_when_env="production",
    ),
]

OPTIONAL_VARS: List[EnvVar] = [
    EnvVar("ACLED_API_KEY", False, "ACLED conflict events API key"),
    EnvVar("ACLED_EMAIL", False, "ACLED registered email"),
    EnvVar("AISHUB_API_KEY", False, "AISHub vessel tracking API key"),
    EnvVar("NASA_FIRMS_MAP_KEY", False, "NASA FIRMS fire/disaster API key"),
    EnvVar("SLACK_WEBHOOK_URL", False, "Slack alerting webhook"),
    EnvVar("CORS_ALLOWED_ORIGINS", False, "Comma-separated CORS allowlist"),
    EnvVar("MLFLOW_TRACKING_URI", False, "MLflow tracking server URI"),
    EnvVar("TIMESCALE_URL", False, "TimescaleDB DSN for score/event history"),
]


def load_env_file(path: Path) -> None:
    """Load .env file into os.environ (without overwriting existing values)."""
    if not path.exists():
        print(f"warn: env file {path} not found", file=sys.stderr)
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


def check_var(var: EnvVar, current_env: str) -> Optional[str]:
    """Return error message if var is missing in a way that matters."""
    value = os.getenv(var.name, "")
    if var.required and not value:
        if var.only_when_env and var.only_when_env != current_env:
            return None  # not required in this env
        return f"❌ {var.name}: missing (required) — {var.description}"
    if not value and not var.required:
        return f"⚠️  {var.name}: not set (optional) — {var.description}"
    return None  # ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat missing optional vars as failures",
    )
    args = parser.parse_args()

    if args.env_file:
        load_env_file(args.env_file)

    current_env = os.getenv("ENVIRONMENT", "development").lower()
    print(f"Validating environment for ENVIRONMENT={current_env!r}\n")

    missing_required: List[str] = []
    missing_optional: List[str] = []

    for var in REQUIRED_VARS:
        msg = check_var(var, current_env)
        if msg:
            missing_required.append(msg)

    for var in OPTIONAL_VARS:
        msg = check_var(var, current_env)
        if msg:
            missing_optional.append(msg)

    if missing_required:
        print("Required variables:")
        for m in missing_required:
            print(f"  {m}")
        print()

    if missing_optional:
        print("Optional variables:")
        for m in missing_optional:
            print(f"  {m}")
        print()

    if not missing_required and not missing_optional:
        print("✅ All environment variables are configured.")
        return 0

    if missing_required:
        print("FAILED: required variables missing.", file=sys.stderr)
        return 1

    if args.strict and missing_optional:
        print("FAILED (strict mode): optional variables missing.", file=sys.stderr)
        return 1

    print("OK: all required variables present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
