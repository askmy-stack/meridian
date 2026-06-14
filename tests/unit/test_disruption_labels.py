"""Unit tests for disruption label loading."""

from __future__ import annotations

from pathlib import Path

from src.intelligence.disruption_labels import (
    load_disruption_labels,
    slugify_supplier_name,
)


def test_slugify_supplier_name() -> None:
    assert slugify_supplier_name("Acme Electronics Ltd") == "acme-electronics-ltd"
    assert slugify_supplier_name("Taiwan Semiconductor Corp") == "taiwan-semiconductor-corp"


def test_load_disruption_labels_from_repo_csv() -> None:
    labels_path = Path(__file__).resolve().parents[2] / "data" / "disruption_labels.csv"
    labels = load_disruption_labels(labels_path)
    assert len(labels) >= 25
    # Repo ships 50+ labeled rows aggregated across suppliers
    row_count = sum(1 for _ in labels_path.open(encoding="utf-8")) - 1
    assert row_count >= 50
    assert labels["taiwan-semiconductor-corp"] == 1
    assert labels["seoul-precision-parts"] == 0


def test_load_disruption_labels_aggregates_positive() -> None:
    labels_path = Path(__file__).resolve().parents[2] / "data" / "disruption_labels.csv"
    labels = load_disruption_labels(labels_path)
    # Rotterdam has both disrupted and stable rows — should aggregate to 1
    assert labels["rotterdam-components"] == 1
