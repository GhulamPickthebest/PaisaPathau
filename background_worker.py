"""Background worker: refresh provider snapshot every N seconds."""

from __future__ import annotations

import threading
import time

from config import settings
from output import write_latest_json
from rate_merge import merge_payloads
from scheduler import fetch_live_payload
from snapshot_store import snapshot_store
from utils import logger

_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()


def refresh_snapshot_once(
    send_amount: float | None = None,
    skip_browser: bool | None = None,
) -> dict:
    """Fetch providers, merge with last good data, and store snapshot."""
    amount = send_amount or settings.send_amount
    browser_skipped = (
        settings.live_api_skip_browser if skip_browser is None else skip_browser
    )
    logger.info(
        "Snapshot refresh started (send_amount=%s, skip_browser=%s)",
        amount,
        browser_skipped,
    )
    started = time.perf_counter()
    new_payload = fetch_live_payload(
        send_amount=amount,
        skip_browser=browser_skipped,
    )
    previous = snapshot_store.get()
    merged = merge_payloads(
        new_payload,
        previous,
        refresh_seconds=settings.live_api_cache_seconds,
    )
    merged["fetch_duration_seconds"] = round(time.perf_counter() - started, 2)
    merged["skip_browser"] = browser_skipped
    snapshot_store.set(merged)
    try:
        write_latest_json(merged)
    except Exception as exc:
        logger.warning("Could not write latest_rates.json: %s", exc)
    logger.info(
        "Snapshot refresh complete in %ss (%s rates)",
        merged["fetch_duration_seconds"],
        len(merged.get("all_rates", [])),
    )
    return merged


def _worker_loop() -> None:
    while not _stop_event.is_set():
        try:
            refresh_snapshot_once()
        except Exception as exc:
            logger.exception("Snapshot refresh failed: %s", exc)
        if _stop_event.wait(settings.live_api_cache_seconds):
            break


def start_snapshot_worker() -> None:
    """Start the 60s background refresh loop (idempotent)."""
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        name="snapshot-worker",
        daemon=True,
    )
    _worker_thread.start()
    logger.info(
        "Snapshot worker started (refresh every %ss)",
        settings.live_api_cache_seconds,
    )


def stop_snapshot_worker() -> None:
    _stop_event.set()
