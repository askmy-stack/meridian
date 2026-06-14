"""Unit tests for SCRI backtest script logic."""

from __future__ import annotations

from scripts.backtest_scri import nearest_snapshot_date, run_backtest


def test_nearest_snapshot_date_on_or_before() -> None:
    available = ["20260101", "20260201", "20260301"]
    assert nearest_snapshot_date("2026-02-15", available) == "20260201"
    assert nearest_snapshot_date("2026-01-10", available) == "20260101"


def test_run_backtest_metrics() -> None:
    labels = [
        {"supplier_id": "sup-a", "event_date": "2026-03-15", "disrupted_30d": "1"},
        {"supplier_id": "sup-b", "event_date": "2026-03-15", "disrupted_30d": "0"},
    ]
    snapshots = {
        "20260301": {"sup-a": 0.75, "sup-b": 0.35},
        "20260310": {"sup-a": 0.80, "sup-b": 0.30},
    }
    metrics = run_backtest(labels, snapshots, risk_threshold=0.55, top_k=2)
    assert metrics["status"] == "ok"
    assert metrics["true_positives"] >= 1
    assert metrics["precision_at_k"] is not None


def test_run_backtest_no_snapshots() -> None:
    metrics = run_backtest([], {})
    assert metrics["status"] == "no_snapshots"
