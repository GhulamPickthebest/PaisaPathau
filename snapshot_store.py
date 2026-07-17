"""Thread-safe stored snapshot for the read-only live API."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DATA_DIR
from utils import logger

SNAPSHOT_PATH = DATA_DIR / "live_snapshot.json"


def _parse_last_updated(value: Any) -> float | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


class SnapshotStore:
    def __init__(self, path: Path = SNAPSHOT_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._payload: dict[str, Any] | None = None
        self._saved_at_wall: float | None = None
        self._load_from_disk()

    def get(self) -> dict[str, Any] | None:
        with self._lock:
            if self._payload is None:
                return None
            return dict(self._payload)

    def age_seconds(self) -> int | None:
        with self._lock:
            if self._saved_at_wall is None:
                return None
            return max(0, int(time.time() - self._saved_at_wall))

    def set(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._payload = dict(payload)
            parsed = _parse_last_updated(payload.get("last_updated"))
            self._saved_at_wall = parsed if parsed is not None else time.time()
            self._write_disk_unlocked()

    def _load_from_disk(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._payload = data
                parsed = _parse_last_updated(data.get("last_updated"))
                self._saved_at_wall = parsed if parsed is not None else time.time()
                logger.info(
                    "Loaded snapshot from %s (age=%ss)",
                    self._path,
                    self.age_seconds(),
                )
        except Exception as exc:
            logger.warning("Could not load snapshot file: %s", exc)

    def _write_disk_unlocked(self) -> None:
        if self._payload is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except Exception as exc:
            logger.warning("Could not write snapshot file: %s", exc)


snapshot_store = SnapshotStore()
