"""Wise live rates API (no auth required)."""

from __future__ import annotations

import requests

from config import settings
from constants import ACTIVE_SEND_CURRENCIES
from models import RateRecord, utc_now_iso
from tier_a.base import BaseApiScraper
from utils import logger, retry


class WiseScraper(BaseApiScraper):
    provider_name = "Wise"
    BASE_URL = "https://wise.com/rates/live"

    @retry(exceptions=(requests.RequestException, ValueError, KeyError))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        url = f"{self.BASE_URL}?source={from_currency}&target=NPR"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        rate = float(data.get("rate", data.get("value")))
        if not rate:
            raise ValueError(f"Unexpected Wise API response: {data}")
        fee = 0.0  # Wise API returns mid-market rate; fee varies by payment method
        net_send, receive = self._compute(rate, fee)

        return RateRecord(
            provider=self.provider_name,
            from_currency=from_currency,
            to_currency="NPR",
            send_amount=self.send_amount,
            exchange_rate=rate,
            fee=fee,
            net_send_amount=net_send,
            receive_amount=receive,
            transfer_speed="1-2 business days",
            delivery_method="Bank transfer",
            timestamp=utc_now_iso(),
            source="api",
            status="ok",
        )

    def fetch_all(self) -> list[RateRecord]:
        records: list[RateRecord] = []
        for currency in ACTIVE_SEND_CURRENCIES:
            try:
                records.append(self.fetch_corridor(currency))
                logger.info("Wise %s -> NPR: ok", currency)
            except Exception as exc:
                logger.error("Wise %s failed: %s", currency, exc)
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

    def _compute(self, rate: float, fee: float) -> tuple[float, float]:
        net_send = round(self.send_amount - fee, 2)
        receive = round(net_send * rate, 2)
        return net_send, receive
