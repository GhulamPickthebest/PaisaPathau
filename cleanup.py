"""Retention cleanup for timestamped JSON snapshot files."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import DATA_DIR
from utils import logger

SNAPSHOT_RETENTION_DAYS = 3
SNAPSHOT_PATTERN = "rates_*.json"
SNAPSHOT_STAMP_FORMAT = "%Y%m%d_%H%M"
PROTECTED_JSON_FILES = {"latest_rates.json"}


def _snapshot_timestamp(path: Path) -> datetime | None:
    if not path.name.startswith("rates_") or path.name in PROTECTED_JSON_FILES:
        return None
    stamp = path.stem.removeprefix("rates_")
    try:
        return datetime.strptime(stamp, SNAPSHOT_STAMP_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def cleanup_old_snapshots(
    data_dir: Path = DATA_DIR,
    retention_days: int | None = None,
) -> list[Path]:
    """Delete rates_YYYYMMDD_HHMM.json files older than retention_days."""
    days = retention_days if retention_days is not None else SNAPSHOT_RETENTION_DAYS
    if days <= 0:
        logger.debug("Snapshot cleanup disabled (retention_days=%s)", days)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted: list[Path] = []

    for path in sorted(data_dir.glob(SNAPSHOT_PATTERN)):
        if path.name in PROTECTED_JSON_FILES:
            continue

        snapshot_time = _snapshot_timestamp(path)
        if snapshot_time is None:
            logger.warning("Skipping snapshot with unexpected name: %s", path.name)
            continue

        if snapshot_time < cutoff:
            path.unlink()
            deleted.append(path)
            logger.info("Deleted old snapshot %s", path.name)

    if deleted:
        logger.info(
            "Snapshot cleanup removed %s file(s) older than %s days",
            len(deleted),
            days,
        )
    else:
        logger.debug("Snapshot cleanup: nothing to delete (retention=%s days)", days)

    return deleted
