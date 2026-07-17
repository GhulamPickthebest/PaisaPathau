"""Background workers: API snapshot every 60s; browser providers on a slower cycle.

API refreshes never wait on Playwright. A hung browser scrape cannot freeze rates.
"""

from __future__ import annotations

import threading
import time

from config import settings
from models import utc_now_iso
from output import write_latest_json
from rate_merge import merge_payloads, merge_rate_records
from scheduler import fetch_browser_tiers, fetch_live_payload
from snapshot_store import snapshot_store
from utils import logger

_api_thread: threading.Thread | None = None
_browser_thread: threading.Thread | None = None
_stop_event = threading.Event()
_snapshot_lock = threading.Lock()


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
    if label in ("api", "full"):
        try:
            write_latest_json(merged)
        except Exception as exc:
            logger.warning("Could not write latest_rates.json: %s", exc)
    logger.info(
        "%s snapshot refresh complete in %ss (%s rates, age reset)",
        label.capitalize(),
        merged["fetch_duration_seconds"],
        len(merged.get("all_rates", [])),
    )
    return merged


def refresh_api_snapshot_once(send_amount: float | None = None) -> dict:
    """Fetch API providers only and merge into the snapshot (never uses Playwright)."""
    amount = send_amount or settings.send_amount
    logger.info("API snapshot refresh started (send_amount=%s)", amount)
    started = time.perf_counter()
    new_payload = fetch_live_payload(send_amount=amount, skip_browser=True)
    with _snapshot_lock:
        return _apply_snapshot(
            new_payload,
            browser_skipped=True,
            started=started,
            label="api",
        )


def refresh_browser_snapshot_once(send_amount: float | None = None) -> dict | None:
    """Fetch browser providers and merge into the existing snapshot."""
    if settings.live_api_skip_browser:
        return None
    amount = send_amount or settings.send_amount
    logger.info("Browser snapshot refresh started (send_amount=%s)", amount)
    started = time.perf_counter()
    records, errors = fetch_browser_tiers(amount)
    previous = snapshot_store.get()
    if not previous:
        logger.warning("Browser refresh skipped — no API snapshot yet")
        return None

    new_rate_dicts = [record.to_dict() for record in records]
    merged_rates = merge_rate_records(
        new_rate_dicts,
        previous.get("all_rates", []),
    )
    partial = dict(previous)
    partial["last_updated"] = utc_now_iso()
    partial["all_rates"] = merged_rates
    if errors:
        partial["errors"] = list(dict.fromkeys((previous.get("errors") or []) + errors))

    with _snapshot_lock:
        merged = dict(partial)
        merged["fetch_mode"] = "snapshot"
        merged["cached"] = True
        merged["snapshot_refresh_seconds"] = settings.live_api_cache_seconds
        merged["fetch_duration_seconds"] = round(time.perf_counter() - started, 2)
        merged["skip_browser"] = False
        merged["refresh_kind"] = "browser"
        snapshot_store.set(merged)
    logger.info(
        "Browser snapshot refresh complete in %ss (%s browser records)",
        merged["fetch_duration_seconds"],
        len(records),
    )
    return merged


def _api_worker_loop() -> None:
    while not _stop_event.is_set():
        try:
            refresh_api_snapshot_once()
        except Exception as exc:
            logger.exception("API snapshot refresh failed: %s", exc)
        if _stop_event.wait(settings.live_api_cache_seconds):
            break


def _browser_worker_loop() -> None:
    interval = max(60, settings.live_api_browser_refresh_seconds)
    # Let the first API refresh land before browsers start.
    if _stop_event.wait(15):
        return
    while not _stop_event.is_set():
        try:
            refresh_browser_snapshot_once()
        except Exception as exc:
            logger.exception("Browser snapshot refresh failed: %s", exc)
        if _stop_event.wait(interval):
            break


def start_snapshot_worker() -> None:
    """Start API + browser background refresh loops (idempotent)."""
    global _api_thread, _browser_thread
    if _api_thread and _api_thread.is_alive():
        return
    _stop_event.clear()
    _api_thread = threading.Thread(
        target=_api_worker_loop,
        name="snapshot-api-worker",
        daemon=True,
    )
    _api_thread.start()
    logger.info(
        "API snapshot worker started (every %ss)",
        settings.live_api_cache_seconds,
    )

    if not settings.live_api_skip_browser:
        _browser_thread = threading.Thread(
            target=_browser_worker_loop,
            name="snapshot-browser-worker",
            daemon=True,
        )
        _browser_thread.start()
        logger.info(
            "Browser snapshot worker started (every %ss)",
            settings.live_api_browser_refresh_seconds,
        )


def stop_snapshot_worker() -> None:
    _stop_event.set()


# Backwards-compatible aliases used by older tests / scripts
def refresh_snapshot_once(
    send_amount: float | None = None,
    skip_browser: bool | None = None,
) -> dict:
    if skip_browser is False and not settings.live_api_skip_browser:
        refresh_api_snapshot_once(send_amount)
        result = refresh_browser_snapshot_once(send_amount)
        return result or snapshot_store.get() or {}
    return refresh_api_snapshot_once(send_amount)
