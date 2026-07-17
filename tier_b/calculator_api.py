"""Shared helpers for provider calculator REST APIs (Tier B)."""

from __future__ import annotations

import time
from typing import Any

import requests

from config import settings
from models import RateRecord, utc_now_iso
from provider_cooldown import is_cooling_down, mark_rate_limited, remaining_seconds
from utils import logger, retry, PermanentScraperError

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://www.remitly.com",
    "Referer": "https://www.remitly.com/",
}


class CalculatorApiScraper:
    """Base for providers exposing public calculator/estimate endpoints."""

    provider_name: str = "Unknown"
    corridors: list[str] = []
    source_label: str = "scraper"

    def __init__(self, send_amount: float | None = None, browser=None, **_kwargs) -> None:
        self.send_amount = send_amount or settings.send_amount
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_all(self) -> list[RateRecord]:
        if is_cooling_down(self.provider_name):
            wait = remaining_seconds(self.provider_name)
            logger.warning(
                "%s skipped — cooling down %ss after rate limit",
                self.provider_name,
                wait,
            )
            return [
                RateRecord.error_record(
                    self.provider_name,
                    currency,
                    self.send_amount,
                    source=self.source_label,
                    error_message=f"Rate limited; retry in {wait}s",
                )
                for currency in self.corridors
            ]

        records: list[RateRecord] = []
        for currency in self.corridors:
            try:
                corridor_records = self.fetch_corridor_records(currency)
                records.extend(corridor_records)
                if any(r.status == "ok" for r in corridor_records):
                    logger.info("%s %s -> NPR: ok", self.provider_name, currency)
            except PermanentScraperError as exc:
                logger.error("%s %s failed: %s", self.provider_name, currency, exc)
                records.append(
                    RateRecord.error_record(
                        self.provider_name,
                        currency,
                        self.send_amount,
                        source=self.source_label,
                        error_message=str(exc),
                    )
                )
            except Exception as exc:
                logger.error("%s %s failed: %s", self.provider_name, currency, exc)
                records.append(
                    RateRecord.error_record(
                        self.provider_name,
                        currency,
                        self.send_amount,
                        source=self.source_label,
                        error_message=str(exc),
                    )
                )
            time.sleep(0.5)
        return records

    def fetch_corridor_records(self, from_currency: str) -> list[RateRecord]:
        return [self.fetch_corridor(from_currency)]

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        raise NotImplementedError

    @retry(exceptions=(requests.RequestException, ValueError, KeyError))
    def _get_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.get(url, timeout=25, **kwargs)
        if response.status_code == 429:
            mark_rate_limited(self.provider_name, seconds=300)
            raise PermanentScraperError(
                f"{self.provider_name} rate limited (429); cooling down 300s"
            )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data and "error_key" in data[0]:
            raise ValueError(data[0].get("message", "API error"))
        return data

    def _build_record(
        self,
        from_currency: str,
        exchange_rate: float,
        fee: float,
        receive_amount: float | None = None,
        transfer_speed: str = "",
        delivery_method: str = "",
        customer_type: str = "",
        rate_label: str = "",
        send_amount: float | None = None,
    ) -> RateRecord:
        amount = send_amount if send_amount is not None else self.send_amount
        net_send = round(amount - fee, 2)
        receive = (
            receive_amount
            if receive_amount is not None
            else round(net_send * exchange_rate, 2)
        )
        return RateRecord(
            provider=self.provider_name,
            from_currency=from_currency,
            to_currency="NPR",
            send_amount=amount,
            exchange_rate=exchange_rate,
            fee=round(fee, 2),
            net_send_amount=net_send,
            receive_amount=round(receive, 2),
            transfer_speed=transfer_speed,
            delivery_method=delivery_method,
            customer_type=customer_type,
            rate_label=rate_label,
            timestamp=utc_now_iso(),
            source=self.source_label,
            status="ok",
        )

    @staticmethod
    def _effective_rate(send_amount: float, receive_amount: float) -> float:
        if send_amount <= 0:
            raise ValueError("Send amount must be positive")
        return receive_amount / send_amount
