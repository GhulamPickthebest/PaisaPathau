"""Base Playwright scraper with shared browser lifecycle and retry logic."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from config import settings
from models import RateRecord, utc_now_iso
from utils import compute_receive_amount, logger, parse_money_amount, parse_rate_from_text, retry


class BaseBrowserScraper(ABC):
    provider_name: str = "Unknown"
    corridors: list[str] = []

    def __init__(self, browser: Browser | None = None, send_amount: float | None = None) -> None:
        self._external_browser = browser
        self.send_amount = send_amount or settings.send_amount
        self.timeout = settings.playwright_timeout_ms

    @contextmanager
    def page_context(
        self, context_options: dict[str, Any] | None = None
    ) -> Generator[Page, None, None]:
        launch_args = ["--disable-blink-features=AutomationControlled"]
        ctx_kwargs: dict[str, Any] = {
            "user_agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "viewport": {"width": 1280, "height": 900},
        }
        if context_options:
            ctx_kwargs.update(context_options)

        if self._external_browser:
            context = self._external_browser.new_context(**ctx_kwargs)
            page = context.new_page()
            page.set_default_timeout(self.timeout)
            try:
                yield page
            finally:
                context.close()
        else:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=settings.playwright_headless,
                    args=launch_args,
                )
                context = browser.new_context(**ctx_kwargs)
                page = context.new_page()
                page.set_default_timeout(self.timeout)
                try:
                    yield page
                finally:
                    context.close()
                    browser.close()

    def fetch_all(self) -> list[RateRecord]:
        records: list[RateRecord] = []
        for currency in self.corridors:
            try:
                corridor_records = self.fetch_corridor_records(currency)
                records.extend(corridor_records)
                if any(r.status == "ok" for r in corridor_records):
                    logger.info("%s %s -> NPR: ok", self.provider_name, currency)
                else:
                    logger.warning("%s %s -> NPR: error", self.provider_name, currency)
            except Exception as exc:
                logger.error("%s %s failed: %s", self.provider_name, currency, exc)
                records.append(
                    RateRecord.error_record(
                        self.provider_name,
                        currency,
                        self.send_amount,
                        source="scraper",
                        error_message=str(exc),
                    )
                )
        return records

    def fetch_corridor_records(self, from_currency: str) -> list[RateRecord]:
        return [self.fetch_corridor(from_currency)]

    @abstractmethod
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        ...

    def _build_record(
        self,
        from_currency: str,
        exchange_rate: float,
        fee: float = 0.0,
        receive_amount: float | None = None,
        transfer_speed: str = "",
        delivery_method: str = "",
        customer_type: str = "",
        rate_label: str = "",
    ) -> RateRecord:
        net_send, computed_receive = compute_receive_amount(
            self.send_amount, fee, exchange_rate
        )
        receive = receive_amount if receive_amount is not None else computed_receive
        return RateRecord(
            provider=self.provider_name,
            from_currency=from_currency,
            to_currency="NPR",
            send_amount=self.send_amount,
            exchange_rate=exchange_rate,
            fee=fee,
            net_send_amount=net_send,
            receive_amount=round(receive, 2),
            transfer_speed=transfer_speed,
            delivery_method=delivery_method,
            customer_type=customer_type,
            rate_label=rate_label,
            timestamp=utc_now_iso(),
            source="scraper",
            status="ok",
        )

    def _parse_fee_from_page(self, page: Page) -> float:
        fee_patterns = [
            r"fee[:\s]+(?:[^\d]*)([\d,.]+)",
            r"transfer fee[:\s]+(?:[^\d]*)([\d,.]+)",
            r"([\d,.]+)\s+fee",
        ]
        body = page.inner_text("body")
        for pattern in fee_patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                amount = parse_money_amount(match.group(1))
                if amount is not None:
                    return amount
        return 0.0

    def _wait_for_rate_text(self, page: Page, currency: str) -> float:
        selectors = [
            f"text=1 {currency} =",
            f"text=1{currency}=",
            "[data-testid*='exchange-rate']",
            "[class*='exchange-rate']",
            "[class*='ExchangeRate']",
        ]
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=15000)
                text = page.locator(selector).first.inner_text()
                rate = parse_rate_from_text(text)
                if rate:
                    return rate
            except Exception:
                continue

        body = page.inner_text("body")
        rate = parse_rate_from_text(body)
        if rate:
            return rate
        raise ValueError(f"Could not parse exchange rate for {currency}")

    def _capture_json_response(
        self, page: Page, url_pattern: str
    ) -> dict[str, Any] | None:
        captured: dict[str, Any] | None = None

        def handle_response(response) -> None:
            nonlocal captured
            if url_pattern in response.url and response.status == 200:
                try:
                    captured = response.json()
                except Exception:
                    pass

        page.on("response", handle_response)
        return captured


class SharedBrowser:
    """Manages a single Chromium instance for all Tier B scrapers."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def start(self) -> Browser:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=settings.playwright_headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return self._browser

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> Browser:
        return self.start()

    def __exit__(self, *args) -> None:
        self.stop()
