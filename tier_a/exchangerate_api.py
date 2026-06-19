"""ExchangeRate-API.com mid-market rates."""

from __future__ import annotations

import requests

from config import settings
from constants import ACTIVE_SEND_CURRENCIES
from models import RateRecord, utc_now_iso
from tier_a.base import BaseApiScraper
from utils import logger, retry


class ExchangeRateApiScraper(BaseApiScraper):
    provider_name = "ExchangeRate-API"
    BASE_URL = "https://v6.exchangerate-api.com/v6"

    def __init__(self, send_amount: float | None = None) -> None:
        super().__init__(send_amount)
        self.api_key = settings.exchangerate_api_key

    @retry(exceptions=(requests.RequestException, ValueError, KeyError))
    def _fetch_rates_for_base(self, base: str) -> dict[str, float]:
        if not self.api_key:
            raise ValueError("EXCHANGERATE_API_KEY not configured")
        url = f"{self.BASE_URL}/{self.api_key}/pair/{base}/NPR"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("result") != "success":
            raise ValueError(data.get("error-type", "Unknown API error"))
        return {"NPR": float(data["conversion_rate"])}

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        rates = self._fetch_rates_for_base(from_currency)
        rate = rates["NPR"]
        fee = 0.0
        net_send = round(self.send_amount - fee, 2)
        receive = round(net_send * rate, 2)

        return RateRecord(
            provider=self.provider_name,
            from_currency=from_currency,
            to_currency="NPR",
            send_amount=self.send_amount,
            exchange_rate=rate,
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
        if not self.api_key:
            logger.warning("ExchangeRate-API key missing; skipping")
            return []

        currencies = list(ACTIVE_SEND_CURRENCIES)
        records: list[RateRecord] = []
        for currency in currencies:
            try:
                records.append(self.fetch_corridor(currency))
                logger.info("ExchangeRate-API %s -> NPR: ok", currency)
            except Exception as exc:
                logger.error("ExchangeRate-API %s failed: %s", currency, exc)
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
