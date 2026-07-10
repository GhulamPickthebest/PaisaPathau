"""Read-only live rates API — serves background snapshot refreshed every 60s."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from background_worker import start_snapshot_worker
from config import settings
from snapshot_store import snapshot_store
from stream_fetch import iter_cached_sse_events
from table_view import build_rates_table_rows, render_streaming_rates_html
from utils import logger


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    start_snapshot_worker()
    yield


app = FastAPI(
    title="PaisaPathau Live Rates API",
    description="Serves AUD→NPR rates from a background snapshot (refreshed every 60s).",
    version="2.0.0",
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


def _warming_payload() -> dict[str, Any]:
    return {
        "status": "warming",
        "last_updated": None,
        "send_amount": settings.send_amount,
        "all_rates": [],
        "corridors": [],
        "fetch_mode": "snapshot",
        "cached": False,
        "snapshot_refresh_seconds": settings.live_api_cache_seconds,
        "message": "Background worker is fetching rates. Retry in a few seconds.",
    }


def _get_snapshot_payload() -> dict[str, Any]:
    payload = snapshot_store.get()
    if not payload:
        return _warming_payload()
    result = dict(payload)
    result["fetch_mode"] = "snapshot"
    result["cached"] = True
    age = snapshot_store.age_seconds()
    if age is not None:
        result["snapshot_age_seconds"] = age
    result["snapshot_refresh_seconds"] = settings.live_api_cache_seconds
    return result


@app.get("/health")
def health() -> dict[str, Any]:
    payload = snapshot_store.get()
    return {
        "status": "ok" if payload else "warming",
        "snapshot_ready": payload is not None,
        "snapshot_age_seconds": snapshot_store.age_seconds(),
        "refresh_seconds": settings.live_api_cache_seconds,
    }


@app.get("/", response_class=HTMLResponse)
def rates_table_page(
    send_amount: float | None = Query(None, ge=1, le=1_000_000),
    skip_browser: bool | None = Query(None),
    fresh: bool = Query(False),
) -> HTMLResponse:
    """Browser table — loads instantly from the stored snapshot."""
    amount = send_amount or settings.send_amount
    browser_skipped = (
        settings.live_api_skip_browser if skip_browser is None else skip_browser
    )
    return HTMLResponse(
        render_streaming_rates_html(amount, browser_skipped, fresh),
        headers={"Cache-Control": f"public, max-age={settings.live_api_cache_seconds}"},
    )


@app.get("/data/latest_rates/stream")
def latest_rates_stream(
    send_amount: float | None = Query(None, ge=1, le=1_000_000),
    skip_browser: bool | None = Query(None),
    fresh: bool = Query(False),
) -> StreamingResponse:
    """Replay the current snapshot as SSE (instant, no live scrape)."""
    payload = _get_snapshot_payload()
    return StreamingResponse(
        iter_cached_sse_events(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": f"public, max-age={settings.live_api_cache_seconds}",
            "Connection": "keep-alive",
            "X-Fetch-Mode": "snapshot",
        },
    )


@app.get("/data/rates_table.json")
def rates_table_json(
    send_amount: float | None = Query(None, ge=1, le=1_000_000),
    skip_browser: bool | None = Query(None),
    fresh: bool = Query(False),
) -> JSONResponse:
    payload = _get_snapshot_payload()
    table_payload = {
        "last_updated": payload.get("last_updated"),
        "send_amount": payload.get("send_amount"),
        "from_currency": "AUD",
        "to_currency": "NPR",
        "cached": payload.get("cached", False),
        "fetch_mode": "snapshot",
        "snapshot_age_seconds": payload.get("snapshot_age_seconds"),
        "snapshot_refresh_seconds": settings.live_api_cache_seconds,
        "rows": build_rates_table_rows(payload),
        "status": payload.get("status", "ok"),
    }
    return JSONResponse(
        table_payload,
        headers={
            "Cache-Control": f"public, max-age={settings.live_api_cache_seconds}",
            "X-Fetch-Mode": "snapshot",
        },
    )


@app.get("/data/latest_rates.json")
def latest_rates(
    send_amount: float | None = Query(None, ge=1, le=1_000_000),
    skip_browser: bool | None = Query(None),
    fresh: bool = Query(False, description="Ignored — API always serves stored snapshot"),
) -> JSONResponse:
    payload = _get_snapshot_payload()
    return JSONResponse(
        payload,
        headers={
            "Cache-Control": f"public, max-age={settings.live_api_cache_seconds}",
            "X-Fetch-Mode": "snapshot",
        },
    )


@app.get("/data/aud_npr_transfer_methods.json")
def transfer_methods(
    send_amount: float | None = Query(None, ge=1, le=1_000_000),
    skip_browser: bool | None = Query(None),
    fresh: bool = Query(False),
) -> JSONResponse:
    payload = _get_snapshot_payload()
    matrix = dict(payload.get("aud_npr_transfer_methods") or {})
    matrix["cached"] = payload.get("cached", False)
    matrix["fetch_mode"] = "snapshot"
    matrix["snapshot_age_seconds"] = payload.get("snapshot_age_seconds")
    return JSONResponse(
        matrix,
        headers={
            "Cache-Control": f"public, max-age={settings.live_api_cache_seconds}",
            "X-Fetch-Mode": "snapshot",
        },
    )
