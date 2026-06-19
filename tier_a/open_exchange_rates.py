"""Open Exchange Rates backup mid-market source."""

from __future__ import annotations

import requests

from config import settings
from constants import ACTIVE_SEND_CURRENCIES
from models import RateRecord, utc_now_iso
from tier_a.base import BaseApiScraper
from utils import logger, retry


class OpenExchangeRatesScraper(BaseApiScraper):
    provider_name = "Open Exchange Rates"
    BASE_URL = "https://openexchangerates.org/api/latest.json"

    def __init__(self, send_amount: float | None = None) -> None:
        super().__init__(send_amount)
        self.app_id = settings.open_exchange_rates_app_id
        self._rates_cache: dict[str, float] | None = None

    @retry(exceptions=(requests.RequestException, ValueError, KeyError))
    def _load_rates(self) -> dict[str, float]:
        if self._rates_cache:
            return self._rates_cache
        if not self.app_id:
            raise ValueError("OPEN_EXCHANGE_RATES_APP_ID not configured")
        response = requests.get(
            self.BASE_URL,
            params={"app_id": self.app_id},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        self._rates_cache = {k: float(v) for k, v in data["rates"].items()}
        return self._rates_cache

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        rates = self._load_rates()
        if from_currency not in rates or "NPR" not in rates:
            raise ValueError(f"Rate not available for {from_currency}/NPR")

        # OXR rates are USD-based; convert cross rate
        if from_currency == "USD":
            rate = rates["NPR"]
        else:
            rate = rates["NPR"] / rates[from_currency]

        fee = 0.0
        net_send = round(self.send_amount - fee, 2)
        receive = round(net_send * rate, 2)

        return RateRecord(
            provider=self.provider_name,
            from_currency=from_currency,
            to_currency="NPR",
            send_amount=self.send_amount,
            exchange_rate=round(rate, 6),
            fee=fee,
            net_send_amount=net_send,
            receive_amount=receive,
            transfer_speed="Mid-market",
            delivery_method="Reference rate",
            timestamp=utc_now_iso(),
            source="api",
            status="ok",
        )

    def fetch_all(self) -> list[RateRecord]:
        if not self.app_id:
            logger.warning("Open Exchange Rates app ID missing; skipping")
            return []

        currencies = list(ACTIVE_SEND_CURRENCIES)
        records: list[RateRecord] = []
        for currency in currencies:
            try:
                records.append(self.fetch_corridor(currency))
                logger.info("Open Exchange Rates %s -> NPR: ok", currency)
            except Exception as exc:
                logger.error("Open Exchange Rates %s failed: %s", currency, exc)
                records.append(
                    RateRecord.error_record(
                        self.provider_name,
                        currency,
                        self.send_amount,
                        source="api",
                        error_message=str(exc),
                    )
                )
        return records
