"""Orchestrates Tier A/B/C fetch cycles and output persistence."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from alerting import alert_on_high_failure_rate
from cleanup import cleanup_old_snapshots
from config import settings
from models import PipelineResult, RateRecord
from output import write_all_outputs
from storage import insert_rates
from tier_a.exchangerate_api import ExchangeRateApiScraper
from tier_a.open_exchange_rates import OpenExchangeRatesScraper
from tier_a.wise import WiseScraper
from tier_b import API_SCRAPERS, BROWSER_SCRAPERS
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

    for scraper_cls in API_SCRAPERS:
        name = scraper_cls.provider_name
        try:
            scraper = scraper_cls(send_amount=send_amount)
            records.extend(scraper.fetch_all())
        except Exception as exc:
            msg = f"Tier B {name} failed: {exc}"
            logger.error(msg)
            errors.append(msg)

    if api_only:
        return records, errors

    with SharedBrowser() as browser:
        for scraper_cls in BROWSER_SCRAPERS:
            name = scraper_cls.provider_name
            try:
                scraper = scraper_cls(browser=browser, send_amount=send_amount)
                records.extend(scraper.fetch_all())
            except Exception as exc:
                msg = f"Tier B {name} failed: {exc}"
                logger.error(msg)
                errors.append(msg)

    return records, errors


def fetch_tier_c(send_amount: float) -> tuple[list[RateRecord], list[str]]:
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

    all_records: list[RateRecord] = []
    all_errors: list[str] = []

    tier_results = [
        fetch_tier_a(amount),
        fetch_tier_b(amount, skip_browser=skip_browser),
        fetch_tier_c(amount),
    ]
    for records, errors in tier_results:
        all_records.extend(records)
        all_errors.extend(errors)

    result = PipelineResult(all_rates=all_records, errors=all_errors)

    insert_rates(all_records)
    write_all_outputs(result, amount, skip_browser=skip_browser)
    cleanup_old_snapshots()

    total_attempts = len(all_records)
    alert_on_high_failure_rate(
        total_attempts,
        len(result.ok_rates),
        all_errors,
    )

    ok = len(result.ok_rates)
    logger.info(
        "Fetch cycle complete: %s ok / %s total records, %s errors",
        ok,
        total_attempts,
        len(all_errors),
    )
    return result


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
