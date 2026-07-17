"""Orchestrates Tier A/B/C fetch cycles and output persistence."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from alerting import alert_on_high_failure_rate
from cleanup import cleanup_old_snapshots
from config import settings
from constants import TIER_C_CURRENCIES
from models import PipelineResult, RateRecord
from output import build_output_payload, write_all_outputs_from_payload
from storage import insert_rates
from transfer_methods.aud_npr import fetch_aud_npr_transfer_methods
from tier_a.exchangerate_api import ExchangeRateApiScraper
from tier_a.open_exchange_rates import OpenExchangeRatesScraper
from tier_a.wise import WiseScraper
from tier_b import API_SCRAPERS, BROWSER_SCRAPERS, NO_QUOTE_SCRAPERS
from tier_b.base import SharedBrowser
from tier_c import TierCMidMarketFetcher
from utils import logger


def fetch_tier_a(send_amount: float) -> tuple[list[RateRecord], list[str]]:
    records: list[RateRecord] = []
    errors: list[str] = []

    scrapers = [
        WiseScraper(send_amount),
        ExchangeRateApiScraper(send_amount),
        OpenExchangeRatesScraper(send_amount),
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(s.fetch_all): s.provider_name for s in scrapers}
        for future in as_completed(futures):
            name = futures[future]
            try:
                records.extend(future.result())
            except Exception as exc:
                msg = f"Tier A {name} failed: {exc}"
                logger.error(msg)
                errors.append(msg)

    return records, errors


def fetch_tier_b(send_amount: float, skip_browser: bool = False) -> tuple[list[RateRecord], list[str]]:
    if skip_browser:
        logger.info("Skipping Tier B browser scrapers")
        api_only = True
    else:
        api_only = False

    records: list[RateRecord] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=len(API_SCRAPERS)) as executor:
        futures = {
            executor.submit(scraper_cls(send_amount=send_amount).fetch_all): scraper_cls.provider_name
            for scraper_cls in API_SCRAPERS
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                records.extend(future.result())
            except Exception as exc:
                msg = f"Tier B {name} failed: {exc}"
                logger.error(msg)
                errors.append(msg)

    for scraper_cls in NO_QUOTE_SCRAPERS:
        name = scraper_cls.provider_name
        try:
            records.extend(scraper_cls(send_amount=send_amount).fetch_all())
        except Exception as exc:
            msg = f"Tier B {name} failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    if api_only:
        return records, errors

    # One Chromium instance per provider — avoids OOM on Railway (~512MB RAM).
    for scraper_cls in BROWSER_SCRAPERS:
        name = scraper_cls.provider_name
        try:
            with SharedBrowser() as browser:
                scraper = scraper_cls(browser=browser, send_amount=send_amount)
                records.extend(scraper.fetch_all())
        except Exception as exc:
            msg = f"Tier B {name} failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    return records, errors


def fetch_tier_c(send_amount: float) -> tuple[list[RateRecord], list[str]]:
    if not TIER_C_CURRENCIES:
        logger.info("Tier C skipped (no mid-market currencies configured)")
        return [], []
    records: list[RateRecord] = []
    errors: list[str] = []
    try:
        fetcher = TierCMidMarketFetcher(send_amount)
        records.extend(fetcher.fetch_all())
    except Exception as exc:
        msg = f"Tier C failed: {exc}"
        logger.error(msg)
        errors.append(msg)
    return records, errors


def run_fetch_cycle(
    send_amount: float | None = None,
    skip_browser: bool = False,
) -> PipelineResult:
    amount = send_amount or settings.send_amount
    logger.info("Starting fetch cycle (send_amount=%s)", amount)

    result, payload = _fetch_and_build_payload(amount, skip_browser=skip_browser)

    insert_rates(result.all_rates)
    write_all_outputs_from_payload(result, payload, amount)
    cleanup_old_snapshots()

    total_attempts = len(result.all_rates)
    alert_on_high_failure_rate(
        total_attempts,
        len(result.ok_rates),
        result.errors,
    )

    ok = len(result.ok_rates)
    logger.info(
        "Fetch cycle complete: %s ok / %s total records, %s errors",
        ok,
        total_attempts,
        len(result.errors),
    )
    return result


def fetch_live_payload(
    send_amount: float | None = None,
    skip_browser: bool | None = None,
) -> dict:
    """Fetch current provider rates and return JSON payload (no file/DB writes)."""
    started = time.perf_counter()
    amount = send_amount or settings.send_amount
    browser_skipped = (
        settings.live_api_skip_browser if skip_browser is None else skip_browser
    )
    logger.info(
        "Live fetch (send_amount=%s, skip_browser=%s)",
        amount,
        browser_skipped,
    )
    _result, payload = _fetch_and_build_payload(
        amount, skip_browser=browser_skipped
    )
    payload["fetch_mode"] = "live"
    payload["skip_browser"] = browser_skipped
    payload["fetch_duration_seconds"] = round(time.perf_counter() - started, 2)
    return payload


def _fetch_and_build_payload(
    amount: float,
    skip_browser: bool,
) -> tuple[PipelineResult, dict]:
    all_records: list[RateRecord] = []
    all_errors: list[str] = []
    transfer_matrix: dict = {}

    # Never run Playwright tier fetch and transfer-matrix fetch in parallel —
    # that launches two Chromium processes and triggers Railway OOM.
    if skip_browser:
        with ThreadPoolExecutor(max_workers=2) as executor:
            tiers_future = executor.submit(_fetch_all_tiers, amount, skip_browser)
            matrix_future = executor.submit(
                fetch_aud_npr_transfer_methods,
                send_amount=amount,
                skip_browser=skip_browser,
            )
            all_records, all_errors = tiers_future.result()
            transfer_matrix = matrix_future.result()
    else:
        # Browser scrapers first; API quotes last so they match the website at save time.
        browser_records, browser_errors = fetch_browser_tiers(amount)
        all_records.extend(browser_records)
        all_errors.extend(browser_errors)

        with ThreadPoolExecutor(max_workers=2) as executor:
            api_future = executor.submit(_fetch_api_tiers, amount)
            matrix_future = executor.submit(
                fetch_aud_npr_transfer_methods,
                send_amount=amount,
                skip_browser=True,
            )
            api_records, api_errors = api_future.result()
            transfer_matrix = matrix_future.result()
        all_records.extend(api_records)
        all_errors.extend(api_errors)

    result = PipelineResult(all_rates=all_records, errors=all_errors)
    payload = build_output_payload(result, amount, transfer_matrix)
    if all_errors:
        payload["errors"] = all_errors
    if transfer_matrix.get("errors"):
        payload.setdefault("errors", []).extend(transfer_matrix["errors"])
    return result, payload


def _fetch_api_tiers(amount: float) -> tuple[list[RateRecord], list[str]]:
    all_records: list[RateRecord] = []
    all_errors: list[str] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_tier_a, amount): "tier_a",
            executor.submit(fetch_tier_b, amount, skip_browser=True): "tier_b_api",
            executor.submit(fetch_tier_c, amount): "tier_c",
        }
        for future in as_completed(futures):
            try:
                records, errors = future.result()
                all_records.extend(records)
                all_errors.extend(errors)
            except Exception as exc:
                label = futures[future]
                msg = f"{label} failed: {exc}"
                logger.error(msg)
                all_errors.append(msg)

    return all_records, all_errors


def fetch_browser_tiers(amount: float) -> tuple[list[RateRecord], list[str]]:
    """Fetch Playwright-based providers only (one browser at a time)."""
    records: list[RateRecord] = []
    errors: list[str] = []

    for scraper_cls in BROWSER_SCRAPERS:
        name = scraper_cls.provider_name
        try:
            with SharedBrowser() as browser:
                scraper = scraper_cls(browser=browser, send_amount=amount)
                records.extend(scraper.fetch_all())
        except Exception as exc:
            msg = f"Tier B {name} failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    return records, errors


# Backwards-compatible alias
_fetch_browser_tiers = fetch_browser_tiers


def _fetch_all_tiers(
    amount: float, skip_browser: bool
) -> tuple[list[RateRecord], list[str]]:
    all_records: list[RateRecord] = []
    all_errors: list[str] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_tier_a, amount): "tier_a",
            executor.submit(fetch_tier_b, amount, skip_browser): "tier_b",
            executor.submit(fetch_tier_c, amount): "tier_c",
        }
        for future in as_completed(futures):
            try:
                records, errors = future.result()
                all_records.extend(records)
                all_errors.extend(errors)
            except Exception as exc:
                label = futures[future]
                msg = f"{label} failed: {exc}"
                logger.error(msg)
                all_errors.append(msg)

    return all_records, all_errors


def run_scheduler(
    interval_minutes: int = 30,
    skip_browser: bool = False,
) -> None:
    logger.info("Starting scheduler (interval=%s minutes)", interval_minutes)
    while True:
        try:
            run_fetch_cycle(skip_browser=skip_browser)
        except Exception as exc:
            logger.exception("Unhandled error in fetch cycle: %s", exc)
        logger.info("Sleeping %s minutes until next cycle", interval_minutes)
        time.sleep(interval_minutes * 60)
