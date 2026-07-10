"""Thread-safe stored snapshot for the read-only live API."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from config import DATA_DIR
from utils import logger

SNAPSHOT_PATH = DATA_DIR / "live_snapshot.json"


class SnapshotStore:
    def __init__(self, path: Path = SNAPSHOT_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._payload: dict[str, Any] | None = None
        self._saved_at: float | None = None
        self._load_from_disk()

    def get(self) -> dict[str, Any] | None:
        with self._lock:
            if self._payload is None:
                return None
            return dict(self._payload)

    def age_seconds(self) -> int | None:
        with self._lock:
            if self._saved_at is None:
                return None
            return int(time.monotonic() - self._saved_at)

    def set(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._payload = dict(payload)
            self._saved_at = time.monotonic()
            self._write_disk_unlocked()

    def _load_from_disk(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._payload = data
                self._saved_at = time.monotonic()
                logger.info("Loaded snapshot from %s", self._path)
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
