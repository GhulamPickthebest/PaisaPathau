"""Wise remittance quote via public comparisons API (AUD→NPR)."""

from __future__ import annotations

from constants import WISE_TRANSFER_LOCALE, active_corridors
from models import RateRecord
from tier_b.calculator_api import CalculatorApiScraper

WISE_COMPARISONS = "https://wise.com/gateway/v4/comparisons"


class WiseTransferScraper(CalculatorApiScraper):
    provider_name = "Wise"
    corridors = active_corridors(WISE_TRANSFER_LOCALE)

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        response = self.session.get(
            WISE_COMPARISONS,
            params={
                "sourceCurrency": from_currency,
                "targetCurrency": "NPR",
                "sendAmount": self.send_amount,
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://wise.com",
                "Referer": "https://wise.com/",
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        wise = next(
            (p for p in data.get("providers", []) if p.get("alias") == "wise"),
            None,
        )
        if not wise or not wise.get("quotes"):
            raise ValueError(f"Wise transfer quote unavailable for {from_currency}/NPR")

        quote = wise["quotes"][0]
        rate = float(quote["rate"])
        fee = float(quote.get("fee") or 0)
        receive = float(quote.get("receivedAmount") or 0)
        duration = quote.get("deliveryEstimation", {}).get("duration") or {}
        speed = _format_delivery(duration) or "1-2 business days"

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=fee,
            receive_amount=receive,
            transfer_speed=speed,
            delivery_method="Bank transfer",
        )


def _format_delivery(duration: dict) -> str:
    min_d = duration.get("min") or ""
    max_d = duration.get("max") or ""
    if min_d and max_d and min_d != max_d:
        return f"{min_d} - {max_d}"
    return min_d or max_d or ""
