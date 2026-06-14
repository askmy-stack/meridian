"""Async batch writer for TimescaleDB score and event signal history.

TimescaleDB is optional — callers should check ``is_available()`` and skip
gracefully when the service is down (same pattern as Neo4j in unit tests).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import structlog

logger = structlog.get_logger(__name__)

_writer_instance: Optional["TimescaleWriter"] = None


def resolve_timescale_url() -> Optional[str]:
    """Build PostgreSQL DSN from TIMESCALE_URL or discrete env vars."""
    explicit = os.getenv("TIMESCALE_URL")
    if explicit:
        return explicit

    host = os.getenv("TIMESCALE_HOST")
    if not host:
        return None

    user = os.getenv("TIMESCALE_USER") or os.getenv("POSTGRES_USER", "meridian")
    password = os.getenv("TIMESCALE_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
    port = os.getenv("TIMESCALE_PORT", "5433")
    database = os.getenv("TIMESCALE_DB", "meridian_timeseries")
    safe_password = quote_plus(password)
    return f"postgresql://{user}:{safe_password}@{host}:{port}/{database}"


@dataclass
class SupplierScoreRecord:
    """One supplier risk score snapshot for time-series storage."""

    supplier_id: str
    risk_score: float
    risk_category: str
    model_version: str
    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    feature_snapshot: Optional[Dict[str, Any]] = None


@dataclass
class EventSignalRecord:
    """Aggregated event-ingest batch metadata."""

    source: str
    linked_supplier_count: int
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: Optional[str] = None
    severity: Optional[float] = None


class TimescaleWriter:
    """Batch writer for Meridian TimescaleDB hypertables."""

    SCORE_INSERT = """
        INSERT INTO supplier_score_history
            (supplier_id, risk_score, risk_category, model_version, feature_snapshot, scored_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6)
    """

    EVENT_INSERT = """
        INSERT INTO event_signal_history
            (event_id, severity, source, linked_supplier_count, ingested_at)
        VALUES ($1, $2, $3, $4, $5)
    """

    def __init__(self, dsn: Optional[str] = None) -> None:
        self.dsn = dsn or resolve_timescale_url()
        self._available: Optional[bool] = None
        self.logger = logger.bind(component="TimescaleWriter")

    def is_configured(self) -> bool:
        """True when a DSN is present in the environment."""
        return bool(self.dsn)

    def is_available(self) -> bool:
        """Probe connectivity once; cache result for the process lifetime."""
        if not self.is_configured():
            return False
        if self._available is not None:
            return self._available
        self._available = self._probe_sync()
        return self._available

    def _probe_sync(self) -> bool:
        try:
            import psycopg2

            assert self.dsn is not None
            with psycopg2.connect(self.dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            self.logger.info("timescale_available")
            return True
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("timescale_unavailable", error=str(exc))
            return False

    async def write_score_batch(self, records: List[SupplierScoreRecord]) -> int:
        """Insert supplier score history rows; return rows written."""
        if not records or not self.is_available():
            return 0
        return await self._execute_batch(
            self.SCORE_INSERT,
            [
                (
                    r.supplier_id,
                    r.risk_score,
                    r.risk_category,
                    r.model_version,
                    json.dumps(r.feature_snapshot) if r.feature_snapshot else None,
                    r.scored_at,
                )
                for r in records
            ],
        )

    async def write_event_batch(self, records: List[EventSignalRecord]) -> int:
        """Insert event signal history rows; return rows written."""
        if not records or not self.is_available():
            return 0
        return await self._execute_batch(
            self.EVENT_INSERT,
            [
                (
                    r.event_id,
                    r.severity,
                    r.source,
                    r.linked_supplier_count,
                    r.ingested_at,
                )
                for r in records
            ],
        )

    async def _execute_batch(self, query: str, args_list: List[tuple[Any, ...]]) -> int:
        import asyncpg

        assert self.dsn is not None
        conn = await asyncpg.connect(self.dsn, timeout=5)
        try:
            await conn.executemany(query, args_list)
            self.logger.info("timescale_batch_written", rows=len(args_list))
            return len(args_list)
        finally:
            await conn.close()

    def write_score_batch_sync(self, records: List[SupplierScoreRecord]) -> int:
        """Synchronous wrapper for CLI scripts."""
        if not records or not self.is_available():
            return 0
        return asyncio.run(self.write_score_batch(records))

    def write_event_batch_sync(self, records: List[EventSignalRecord]) -> int:
        """Synchronous wrapper for CLI scripts."""
        if not records or not self.is_available():
            return 0
        return asyncio.run(self.write_event_batch(records))


def get_timescale_writer() -> TimescaleWriter:
    """Return process-wide TimescaleWriter singleton."""
    global _writer_instance
    if _writer_instance is None:
        _writer_instance = TimescaleWriter()
    return _writer_instance
