"""Tests for snapshot JSON retention cleanup."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from cleanup import cleanup_old_snapshots


def _write_snapshot(path: Path, stamp: datetime) -> None:
    name = f"rates_{stamp.strftime('%Y%m%d_%H%M')}.json"
    (path / name).write_text('{"ok": true}', encoding="utf-8")


def test_cleanup_deletes_old_snapshots_only(tmp_path: Path):
    now = datetime.now(timezone.utc)
    _write_snapshot(tmp_path, now - timedelta(days=10))
    _write_snapshot(tmp_path, now - timedelta(days=2))
    (tmp_path / "latest_rates.json").write_text("{}", encoding="utf-8")

    deleted = cleanup_old_snapshots(tmp_path, retention_days=7)

    assert len(deleted) == 1
    assert deleted[0].name.startswith("rates_")
    remaining = sorted(p.name for p in tmp_path.glob("rates_*.json"))
    assert len(remaining) == 1
    assert (tmp_path / "latest_rates.json").exists()


def test_cleanup_disabled_when_retention_zero(tmp_path: Path):
    now = datetime.now(timezone.utc)
    _write_snapshot(tmp_path, now - timedelta(days=30))

    deleted = cleanup_old_snapshots(tmp_path, retention_days=0)

    assert deleted == []
    assert len(list(tmp_path.glob("rates_*.json"))) == 1
