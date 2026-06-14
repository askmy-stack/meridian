"""Unit tests for TimescaleDB writer (mocked connection)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.storage.timescale_writer import (
    EventSignalRecord,
    SupplierScoreRecord,
    TimescaleWriter,
    resolve_timescale_url,
)


def test_resolve_timescale_url_from_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESCALE_URL", "postgresql://u:p@host:5433/db")
    monkeypatch.delenv("TIMESCALE_HOST", raising=False)
    assert resolve_timescale_url() == "postgresql://u:p@host:5433/db"


def test_resolve_timescale_url_from_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TIMESCALE_URL", raising=False)
    monkeypatch.setenv("TIMESCALE_HOST", "localhost")
    monkeypatch.setenv("TIMESCALE_PORT", "5433")
    monkeypatch.setenv("TIMESCALE_DB", "meridian_timeseries")
    monkeypatch.setenv("TIMESCALE_USER", "meridian")
    monkeypatch.setenv("TIMESCALE_PASSWORD", "secret")
    url = resolve_timescale_url()
    assert url is not None
    assert "localhost:5433" in url
    assert "meridian_timeseries" in url


def test_writer_not_configured_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TIMESCALE_URL", raising=False)
    monkeypatch.delenv("TIMESCALE_HOST", raising=False)
    writer = TimescaleWriter()
    assert not writer.is_configured()
    assert writer.write_score_batch_sync([]) == 0


def test_write_score_batch_sync_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESCALE_URL", "postgresql://u:p@localhost:5433/db")
    writer = TimescaleWriter()
    with patch.object(writer, "is_available", return_value=False):
        count = writer.write_score_batch_sync(
            [
                SupplierScoreRecord(
                    supplier_id="sup-1",
                    risk_score=0.5,
                    risk_category="MEDIUM",
                    model_version="1.0.0",
                )
            ]
        )
    assert count == 0


@pytest.mark.asyncio
async def test_write_score_batch_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESCALE_URL", "postgresql://u:p@localhost:5433/db")
    writer = TimescaleWriter()
    writer._available = True

    mock_conn = AsyncMock()
    mock_conn.executemany = AsyncMock()
    mock_conn.close = AsyncMock()

    with patch("asyncpg.connect", AsyncMock(return_value=mock_conn)):
        written = await writer.write_score_batch(
            [
                SupplierScoreRecord(
                    supplier_id="sup-1",
                    risk_score=0.7,
                    risk_category="HIGH",
                    model_version="test",
                )
            ]
        )

    assert written == 1
    mock_conn.executemany.assert_called_once()
    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_write_event_batch_sync_delegates_to_async(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESCALE_URL", "postgresql://u:p@localhost:5433/db")
    writer = TimescaleWriter()
    writer._available = True

    with patch.object(writer, "write_event_batch", AsyncMock(return_value=3)) as mock_batch:
        with patch("asyncio.run", side_effect=lambda coro: 3) as mock_run:
            count = writer.write_event_batch_sync(
                [EventSignalRecord(source="graph_loader", linked_supplier_count=5)]
            )
    assert count == 3
    mock_run.assert_called_once()
