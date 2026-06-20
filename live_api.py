"""On-demand live rates API — fetches provider data per request (with short cache)."""

from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from scheduler import fetch_live_payload
from utils import logger


def _warm_cache_background() -> None:
    try:
        logger.info("Warming live API cache on startup...")
        payload = fetch_live_payload()
        _cache_set(
            (settings.send_amount, settings.live_api_skip_browser),
            payload,
        )
        logger.info(
            "Live API cache warmed in %ss",
            payload.get("fetch_duration_seconds", "?"),
        )
    except Exception as exc:
        logger.warning("Live API cache warm-up failed: %s", exc)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    if settings.live_api_warm_cache:
        threading.Thread(target=_warm_cache_background, daemon=True).start()
    yield


app = FastAPI(
    title="PaisaPathau Live Rates API",
    description="Fetches AUD→NPR rates from providers on demand.",
    version="1.0.0",
    lifespan=_lifespan,
)

_origins = [
    origin.strip()
    for origin in settings.live_api_cors_origins.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache_lock = threading.Lock()
_cache: dict[tuple[Any, ...], tuple[float, dict]] = {}


def _cache_get(key: tuple[Any, ...]) -> dict | None:
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        expires_at, payload = entry
        if time.monotonic() >= expires_at:
            _cache.pop(key, None)
            return None
        cached = dict(payload)
        cached["cached"] = True
        cached["cache_age_seconds"] = int(
            settings.live_api_cache_seconds
            - (expires_at - time.monotonic())
        )
        return cached


def _cache_set(key: tuple[Any, ...], payload: dict) -> None:
    with _cache_lock:
        _cache[key] = (
            time.monotonic() + settings.live_api_cache_seconds,
            payload,
        )


def _get_rates_payload(
    send_amount: float,
    skip_browser: bool,
    fresh: bool,
) -> dict:
    cache_key = (send_amount, skip_browser)
    if not fresh and settings.live_api_cache_seconds > 0:
        cached = _cache_get(cache_key)
        if cached:
            logger.info("Live API cache hit (send_amount=%s)", send_amount)
            return cached

    payload = fetch_live_payload(
        send_amount=send_amount,
        skip_browser=skip_browser,
    )
    payload["cached"] = False
    if settings.live_api_cache_seconds > 0:
        _cache_set(cache_key, payload)
    return payload


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/data/latest_rates.json")
def latest_rates(
    send_amount: float | None = Query(None, ge=1, le=1_000_000),
    skip_browser: bool | None = Query(None),
    fresh: bool = Query(False, description="Bypass cache and fetch providers now"),
) -> JSONResponse:
    amount = send_amount or settings.send_amount
    browser_skipped = (
        settings.live_api_skip_browser if skip_browser is None else skip_browser
    )
    payload = _get_rates_payload(amount, browser_skipped, fresh)
    max_age = 0 if fresh else settings.live_api_cache_seconds
    return JSONResponse(
        payload,
        headers={
            "Cache-Control": f"public, max-age={max_age}",
            "X-Fetch-Mode": "live",
        },
    )


@app.get("/data/aud_npr_transfer_methods.json")
def transfer_methods(
    send_amount: float | None = Query(None, ge=1, le=1_000_000),
    skip_browser: bool | None = Query(None),
    fresh: bool = Query(False),
) -> JSONResponse:
    amount = send_amount or settings.send_amount
    browser_skipped = (
        settings.live_api_skip_browser if skip_browser is None else skip_browser
    )
    payload = _get_rates_payload(amount, browser_skipped, fresh)
    matrix = payload.get("aud_npr_transfer_methods") or {}
    matrix["cached"] = payload.get("cached", False)
    matrix["fetch_mode"] = "live"
    max_age = 0 if fresh else settings.live_api_cache_seconds
    return JSONResponse(
        matrix,
        headers={
            "Cache-Control": f"public, max-age={max_age}",
            "X-Fetch-Mode": "live",
        },
    )
