"""Tier C: mid-market exchange rates for additional currencies."""

from __future__ import annotations

from config import settings
from constants import TIER_C_CURRENCIES
from models import RateRecord
from tier_a.exchangerate_api import ExchangeRateApiScraper
from tier_a.open_exchange_rates import OpenExchangeRatesScraper
from tier_a.wise import WiseScraper
from utils import logger


class TierCMidMarketFetcher:
    """Fetch mid-market NPR rates using Tier A APIs with fallback chain."""

    provider_label = "Mid-Market Rate"

    def __init__(self, send_amount: float) -> None:
        self.send_amount = send_amount
        self._wise = WiseScraper(send_amount)
        self._exr = ExchangeRateApiScraper(send_amount)
        self._oxr = OpenExchangeRatesScraper(send_amount)

    def _available_sources(self) -> list[tuple[str, object]]:
        sources: list[tuple[str, object]] = [("Wise", self._wise)]
        if settings.exchangerate_api_key:
            sources.append(("ExchangeRate-API", self._exr))
        if settings.open_exchange_rates_app_id:
            sources.append(("Open Exchange Rates", self._oxr))
        return sources

    def fetch_all(self) -> list[RateRecord]:
        records: list[RateRecord] = []
        for currency in TIER_C_CURRENCIES:
            record = self._fetch_with_fallback(currency)
            records.append(record)
        return records

    def _fetch_with_fallback(self, currency: str) -> RateRecord:
        sources = self._available_sources()
        errors: list[str] = []

        for name, scraper in sources:
            try:
                record = scraper.fetch_corridor(currency)
                record.provider = self.provider_label
                record.delivery_method = f"Mid-market via {name}"
                record.transfer_speed = "Reference"
                logger.info("Tier C %s via %s: ok", currency, name)
                return record
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                logger.warning("Tier C %s via %s failed: %s", currency, name, exc)

        return RateRecord.error_record(
            self.provider_label,
            currency,
            self.send_amount,
            source="api",
            error_message="; ".join(errors) or "No API sources configured",
        )
