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
_fast_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()
_refresh_lock = threading.Lock()
_full_refresh_in_progress = threading.Event()


def _apply_snapshot(
    new_payload: dict,
    *,
    browser_skipped: bool,
    started: float,
    label: str,
) -> dict:
    previous = snapshot_store.get()
    merged = merge_payloads(
        new_payload,
        previous,
        refresh_seconds=settings.live_api_cache_seconds,
    )
    merged["fetch_duration_seconds"] = round(time.perf_counter() - started, 2)
    merged["skip_browser"] = browser_skipped
    merged["refresh_kind"] = label
    snapshot_store.set(merged)
    if label == "full":
        try:
            write_latest_json(merged)
        except Exception as exc:
            logger.warning("Could not write latest_rates.json: %s", exc)
    logger.info(
        "%s snapshot refresh complete in %ss (%s rates)",
        label.capitalize(),
        merged["fetch_duration_seconds"],
        len(merged.get("all_rates", [])),
    )
    return merged


def refresh_snapshot_once(
    send_amount: float | None = None,
    skip_browser: bool | None = None,
) -> dict:
    """Fetch all providers, merge with last good data, and store snapshot."""
    amount = send_amount or settings.send_amount
    browser_skipped = (
        settings.live_api_skip_browser if skip_browser is None else skip_browser
    )
    logger.info(
        "Full snapshot refresh started (send_amount=%s, skip_browser=%s)",
        amount,
        browser_skipped,
    )
    _full_refresh_in_progress.set()
    with _refresh_lock:
        started = time.perf_counter()
        new_payload = fetch_live_payload(
            send_amount=amount,
            skip_browser=browser_skipped,
        )
        merged = _apply_snapshot(
            new_payload,
            browser_skipped=browser_skipped,
            started=started,
            label="full",
        )
    _full_refresh_in_progress.clear()
    return merged


def refresh_api_snapshot_fast(send_amount: float | None = None) -> dict | None:
    """Quick API-only refresh so rates stay close to provider websites."""
    if settings.live_api_fast_refresh_seconds <= 0:
        return None
    if settings.live_api_skip_browser:
        return None
    if _full_refresh_in_progress.is_set():
        return None
    if not _refresh_lock.acquire(blocking=False):
        return None

    amount = send_amount or settings.send_amount
    try:
        logger.info("Fast API snapshot refresh started (send_amount=%s)", amount)
        started = time.perf_counter()
        new_payload = fetch_live_payload(send_amount=amount, skip_browser=True)
        return _apply_snapshot(
            new_payload,
            browser_skipped=True,
            started=started,
            label="fast_api",
        )
    finally:
        _refresh_lock.release()


def _worker_loop() -> None:
    while not _stop_event.is_set():
        try:
            refresh_snapshot_once()
        except Exception as exc:
            logger.exception("Snapshot refresh failed: %s", exc)
        if _stop_event.wait(settings.live_api_cache_seconds):
            break


def _fast_worker_loop() -> None:
    interval = settings.live_api_fast_refresh_seconds
    while not _stop_event.is_set():
        try:
            refresh_api_snapshot_fast()
        except Exception as exc:
            logger.exception("Fast API snapshot refresh failed: %s", exc)
        if _stop_event.wait(interval):
            break


def start_snapshot_worker() -> None:
    """Start background refresh loops (idempotent)."""
    global _worker_thread, _fast_worker_thread
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
        "Snapshot worker started (full refresh every %ss)",
        settings.live_api_cache_seconds,
    )

    if (
        settings.live_api_fast_refresh_seconds > 0
        and not settings.live_api_skip_browser
    ):
        _fast_worker_thread = threading.Thread(
            target=_fast_worker_loop,
            name="snapshot-fast-api-worker",
            daemon=True,
        )
        _fast_worker_thread.start()
        logger.info(
            "Fast API snapshot worker started (every %ss)",
            settings.live_api_fast_refresh_seconds,
        )


def stop_snapshot_worker() -> None:
    _stop_event.set()
