"""Remitly calculator API scraper (internal estimate endpoint)."""

from __future__ import annotations

from urllib.parse import quote

from constants import REMITLY_LOCALE
from models import RateRecord
from tier_b.calculator_api import CalculatorApiScraper

# Remitly ISO3 country codes for conduit parameter
REMITLY_COUNTRY: dict[str, str] = {
    "AUD": "AUS",
    "USD": "USA",
    "GBP": "GBR",
    "CAD": "CAN",
    "NZD": "NZL",
    "EUR": "DEU",
    "AED": "ARE",
}

REMITLY_API = "https://api.remitly.io/v3/calculator/estimate"


class RemitlyScraper(CalculatorApiScraper):
    provider_name = "Remitly"
    corridors = list(REMITLY_LOCALE.keys())

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        source_country = REMITLY_COUNTRY.get(from_currency)
        if not source_country:
            raise ValueError(f"Unsupported corridor: {from_currency}")

        conduit = quote(f"{source_country}:{from_currency}-NPL:NPR", safe="")
        url = (
            f"{REMITLY_API}?conduit={conduit}"
            f"&anchor=SEND&amount={int(self.send_amount)}"
            f"&purpose=OTHER&customer_segment=STANDARD"
            f"&customer_recognition=UNRECOGNIZED&strict_promo=false"
        )

        data = self._get_json(url)
        estimate = data.get("estimate", data)
        rate_data = estimate.get("exchange_rate", {})
        fee_data = estimate.get("fee", {})

        rate = float(
            rate_data.get("promotional_exchange_rate")
            or rate_data.get("base_rate")
            or 0
        )
        fee = float(fee_data.get("total_fee_amount", 0) or 0)
        receive = estimate.get("receive_amount")
        receive_amount = float(receive) if receive is not None else None

        if not rate:
            raise ValueError(f"No rate in Remitly response: {data}")

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=fee,
            receive_amount=receive_amount,
            transfer_speed="Minutes to 3 business days",
            delivery_method="Bank deposit / Cash pickup",
        )
