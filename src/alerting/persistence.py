"""File-backed alert persistence for demo and single-node deployments."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

import structlog

from .slack import Alert, AlertTier

logger = structlog.get_logger(__name__)

DEFAULT_PATH = Path(os.getenv("MERIDIAN_ALERTS_FILE", ".data/alerts.json"))


class AlertStore:
    """Append-only JSON alert store with in-memory cache."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or DEFAULT_PATH
        self._cache: List[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._cache = []
            return
        try:
            self._cache = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("alert_store_load_failed", error=str(exc))
            self._cache = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._cache[-2000:], indent=2), encoding="utf-8")

    def append(self, alert: Alert) -> None:
        self._cache.append(alert.to_dict())
        self._save()

    def list_recent(self, limit: int = 50, tier: Optional[AlertTier] = None) -> List[dict]:
        rows = list(reversed(self._cache))
        if tier is not None:
            rows = [r for r in rows if r.get("tier") == tier.value]
        return rows[:limit]


_store: Optional[AlertStore] = None


def get_alert_store() -> AlertStore:
    global _store
    if _store is None:
        _store = AlertStore()
    return _store
