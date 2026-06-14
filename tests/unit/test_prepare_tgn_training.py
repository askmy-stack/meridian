"""Unit tests for TGN training manifest preparation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.prepare_tgn_training import (
    MIN_SNAPSHOTS_FOR_READY,
    build_manifest,
    discover_snapshots,
    write_manifest,
)


def _write_snapshot(directory: Path, stamp: str, rows: int = 2) -> None:
    path = directory / f"supplier_snapshot_{stamp}.csv"
    lines = ["supplier_id,name,risk_score,events,max_severity"]
    for i in range(rows):
        lines.append(f"s{i},Supplier {i},0.5,1,0.6")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_discover_snapshots_sorted(tmp_path: Path) -> None:
    _write_snapshot(tmp_path, "20260610")
    _write_snapshot(tmp_path, "20260612")

    snapshots = discover_snapshots(tmp_path)

    assert len(snapshots) == 2
    assert snapshots[0].date_stamp == "20260610"
    assert snapshots[1].date_stamp == "20260612"
    assert snapshots[0].row_count == 2


def test_build_manifest_not_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNAPSHOT_DIR", str(tmp_path))
    _write_snapshot(tmp_path, "20260613")

    manifest = build_manifest(discover_snapshots(tmp_path))

    assert manifest["snapshot_count"] == 1
    assert manifest["ready_for_training"] is False
    assert manifest["date_range"]["earliest"] == "20260613"


def test_build_manifest_ready_when_enough_snapshots(tmp_path: Path) -> None:
    for day in range(1, MIN_SNAPSHOTS_FOR_READY + 1):
        _write_snapshot(tmp_path, f"2026060{day}")

    manifest = build_manifest(discover_snapshots(tmp_path))

    assert manifest["snapshot_count"] == MIN_SNAPSHOTS_FOR_READY
    assert manifest["ready_for_training"] is True


def test_write_manifest_creates_json(tmp_path: Path) -> None:
    manifest = {"snapshot_count": 0, "ready_for_training": False}
    out = tmp_path / "tgn_manifest.json"

    write_manifest(manifest, out)

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["snapshot_count"] == 0
