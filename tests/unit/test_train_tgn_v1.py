"""Unit tests for TGN v1 training script (synthetic snapshots, no GPU)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.prepare_tgn_training import build_manifest, discover_snapshots
from scripts.train_tgn_v1 import build_sequences, discover_snapshot_paths, train_gru


@pytest.fixture
def seven_snapshots(tmp_path, monkeypatch):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    for day in range(1, 8):
        stamp = f"2026060{day}"
        path = snapshot_dir / f"supplier_snapshot_{stamp}.csv"
        risk = 0.4 + day * 0.05
        path.write_text(
            "supplier_id,name,risk_score,events,max_severity\n"
            f"supplier-alpha,Alpha Corp,{risk:.2f},1,0.6\n"
            f"supplier-beta,Beta Ltd,{0.3 + day * 0.02:.2f},0,\n",
            encoding="utf-8",
        )
    monkeypatch.setenv("SNAPSHOT_DIR", str(snapshot_dir))
    return snapshot_dir


def test_manifest_ready_with_seven_snapshots(seven_snapshots) -> None:
    snapshots = discover_snapshots(seven_snapshots)
    manifest = build_manifest(snapshots, graph_edges={"affects_edges": 12, "source": "test"})
    assert manifest["ready_for_training"] is True
    assert manifest["snapshot_count"] == 7
    assert manifest["graph_edges"]["affects_edges"] == 12


def test_build_sequences_from_snapshots(seven_snapshots) -> None:
    paths = discover_snapshot_paths()
    sequences = build_sequences(paths, seq_len=3)
    assert len(sequences) >= 4
    assert sequences[0].features.shape == (3, 1)


def test_train_gru_produces_metrics(seven_snapshots) -> None:
    paths = discover_snapshot_paths()
    sequences = build_sequences(paths, seq_len=3)
    model, metrics = train_gru(sequences, epochs=5)
    assert metrics["train_mae"] >= 0.0
    assert metrics["backend"] in ("pytorch_gru", "sklearn_ridge_fallback")


def test_prepare_manifest_writes_json(seven_snapshots, tmp_path) -> None:
    snapshots = discover_snapshots(seven_snapshots)
    manifest = build_manifest(snapshots)
    out = seven_snapshots / "tgn_manifest.json"
    out.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["ready_for_training"] is True
