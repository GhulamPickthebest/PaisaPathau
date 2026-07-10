"""Tests for snapshot store and read-only live API."""

from pathlib import Path

from live_api import _get_snapshot_payload, health
from snapshot_store import SnapshotStore


def test_snapshot_store_persists_to_disk(tmp_path: Path):
    path = tmp_path / "live_snapshot.json"
    store = SnapshotStore(path=path)
    store.set({"last_updated": "t1", "all_rates": [{"provider": "Wise"}]})

    reloaded = SnapshotStore(path=path)
    payload = reloaded.get()
    assert payload is not None
    assert payload["last_updated"] == "t1"


def test_get_snapshot_payload_warming_when_empty(monkeypatch):
    from snapshot_store import snapshot_store

    snapshot_store._payload = None
    snapshot_store._saved_at = None
    payload = _get_snapshot_payload()
    assert payload["status"] == "warming"


def test_health_reports_snapshot_ready(monkeypatch):
    from snapshot_store import snapshot_store

    snapshot_store.set({"last_updated": "t1", "all_rates": []})
    result = health()
    assert result["snapshot_ready"] is True
    assert result["refresh_seconds"] == 60
