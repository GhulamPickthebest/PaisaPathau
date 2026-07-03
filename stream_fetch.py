"""Progressive SSE streaming — emit each provider as it finishes."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from config import settings
from constants import STANDARD_TRANSFER_METHODS
from models import PipelineResult, RateRecord, TransferMethodRow, utc_now_iso
from output import build_output_payload
from table_view import (
    _has_valid_rate,
    _row_from_rate_record,
    _row_from_transfer_method,
    build_rates_table_rows,
)
from transfer_methods.aud_npr import (
    _fetch_instarem_rows,
    _fetch_remitly_rows,
    _fetch_western_union_comparison_rows,
    _fetch_wise_rows,
    _fetch_worldremit_rows,
    _unavailable_rows,
)
from tier_a.exchangerate_api import ExchangeRateApiScraper
from tier_a.open_exchange_rates import OpenExchangeRatesScraper
from tier_a.wise import WiseScraper
from tier_b import API_SCRAPERS, BROWSER_SCRAPERS, NO_QUOTE_SCRAPERS
from tier_b.base import SharedBrowser
from utils import logger

_MATRIX_TABLE_PROVIDERS = {
    "Wise",
    "Remitly",
    "WorldRemit",
    "Instarem",
    "Western Union",
}


def encode_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def encode_keepalive() -> str:
    """SSE comment — keeps proxies/Railway from closing idle connections."""
    return ": keepalive\n\n"


def _table_row_event(row: dict[str, Any]) -> str | None:
    """Emit table_row only for displayable live rates."""
    if row.get("status") not in (None, "ok"):
        return None
    if not _has_valid_rate(row):
        return None
    return encode_sse("table_row", {**row, "status": "ok"})


def iter_cached_sse_events(payload: dict[str, Any]) -> Iterator[str]:
    """Replay a cached payload as SSE events (instant)."""
    yield encode_sse(
        "meta",
        {
            "send_amount": payload.get("send_amount"),
            "from_currency": "AUD",
            "to_currency": "NPR",
            "cached": True,
            "cache_seconds": payload.get("cache_seconds", settings.live_api_cache_seconds),
        },
    )
    for row in build_rates_table_rows(payload):
        event = _table_row_event(row)
        if event:
            yield event
    yield encode_sse(
        "done",
        {
            "cached": True,
            "last_updated": payload.get("last_updated"),
            "fetch_duration_seconds": payload.get("fetch_duration_seconds", 0),
            "total_rates": len(payload.get("all_rates", [])),
        },
    )


def iter_live_sse_events(
    send_amount: float,
    skip_browser: bool,
) -> Iterator[str]:
    """Fetch providers in parallel and yield SSE events as each completes."""
    try:
        yield from _iter_live_sse_events_impl(send_amount, skip_browser)
    except Exception as exc:
        logger.exception("Live SSE stream failed: %s", exc)
        yield encode_sse(
            "done",
            {
                "cached": False,
                "error": str(exc),
                "partial": True,
                "total_rates": 0,
            },
        )


def _iter_live_sse_events_impl(
    send_amount: float,
    skip_browser: bool,
) -> Iterator[str]:
    started = time.perf_counter()
    amount = send_amount or settings.send_amount
    all_records: list[RateRecord] = []
    all_errors: list[str] = []
    transfer_row_objs: list[TransferMethodRow] = []

    yield encode_sse(
        "meta",
        {
            "send_amount": amount,
            "from_currency": "AUD",
            "to_currency": "NPR",
            "cached": False,
            "skip_browser": skip_browser,
            "cache_seconds": settings.live_api_cache_seconds,
        },
    )

    with ThreadPoolExecutor(max_workers=14) as pool:
        futures: dict[Any, tuple[str, str]] = {}

        for scraper in (
            WiseScraper(amount),
            ExchangeRateApiScraper(amount),
            OpenExchangeRatesScraper(amount),
        ):
            fut = pool.submit(scraper.fetch_all)
            futures[fut] = ("reference_rate", scraper.provider_name)

        for scraper_cls in API_SCRAPERS:
            fut = pool.submit(scraper_cls(send_amount=amount).fetch_all)
            futures[fut] = ("tier_b_rate", scraper_cls.provider_name)

        for fetcher in (
            _fetch_remitly_rows,
            _fetch_worldremit_rows,
            _fetch_instarem_rows,
            _fetch_wise_rows,
        ):
            fut = pool.submit(fetcher, amount)
            futures[fut] = ("transfer_method", fetcher.__name__)

        futures[pool.submit(_fetch_western_union_comparison_rows, amount)] = (
            "transfer_method",
            "western_union",
        )

        for scraper_cls in NO_QUOTE_SCRAPERS:
            name = scraper_cls.provider_name
            try:
                records = scraper_cls(send_amount=amount).fetch_all()
                all_records.extend(records)
            except Exception as exc:
                msg = f"Tier B {name} failed: {exc}"
                logger.error(msg)
                all_errors.append(msg)

        for future in as_completed(futures):
            kind, label = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                msg = f"{label} failed: {exc}"
                logger.error(msg)
                all_errors.append(msg)
                continue

            if kind == "transfer_method":
                for row in result:
                    transfer_row_objs.append(row)
                    row_dict = row.to_dict()
                    if row_dict.get("status") != "ok":
                        continue
                    table_row = _row_from_transfer_method(row_dict)
                    event = _table_row_event(table_row)
                    if event:
                        yield event
                continue

            for record in result:
                all_records.append(record)
                if record.status != "ok":
                    continue
                if (
                    kind == "tier_b_rate"
                    and record.provider not in _MATRIX_TABLE_PROVIDERS
                ):
                    event = _table_row_event(_row_from_rate_record(record.to_dict()))
                    if event:
                        yield event

    if not skip_browser:
        for scraper_cls in BROWSER_SCRAPERS:
            name = scraper_cls.provider_name
            yield encode_sse("progress", {"provider": name, "phase": "browser"})
            yield encode_keepalive()
            try:
                with SharedBrowser() as browser:
                    scraper = scraper_cls(browser=browser, send_amount=amount)
                    records = scraper.fetch_all()
                for record in records:
                    all_records.append(record)
                    if record.status != "ok":
                        continue
                    event = _table_row_event(_row_from_rate_record(record.to_dict()))
                    if event:
                        yield event
            except Exception as exc:
                msg = f"Tier B {name} failed: {exc}"
                logger.error(msg)
                all_errors.append(msg)

    transfer_matrix = {
        "last_updated": utc_now_iso(),
        "from_currency": "AUD",
        "to_currency": "NPR",
        "send_amount": amount,
        "transfer_methods": STANDARD_TRANSFER_METHODS,
        "rows": [r.to_dict() for r in transfer_row_objs]
        + [r.to_dict() for r in _unavailable_rows(transfer_row_objs, amount)],
        "errors": all_errors,
    }

    result = PipelineResult(all_rates=all_records, errors=all_errors)
    payload = build_output_payload(result, amount, transfer_matrix)
    payload["fetch_mode"] = "live"
    payload["skip_browser"] = skip_browser
    payload["cached"] = False
    payload["cache_seconds"] = settings.live_api_cache_seconds
    duration = round(time.perf_counter() - started, 2)
    payload["fetch_duration_seconds"] = duration
    if all_errors:
        payload["errors"] = all_errors

    yield encode_sse(
        "done",
        {
            "cached": False,
            "last_updated": payload["last_updated"],
            "fetch_duration_seconds": duration,
            "total_rates": len(all_records),
            "payload": payload,
        },
    )
