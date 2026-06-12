"""Instarem calculator API scraper."""

from __future__ import annotations

from constants import INSTAREM_LOCALE
from models import RateRecord
from tier_b.calculator_api import CalculatorApiScraper

INSTAREM_COUNTRY: dict[str, str] = {
    "AUD": "AU",
    "GBP": "GB",
    "SGD": "SG",
}

FEE_URL = "https://www.instarem.com/api/v1/public/payment-method/fee"
COMPUTED_URL = "https://www.instarem.com/api/v1/public/transaction/computed-value"


class InstaremScraper(CalculatorApiScraper):
    provider_name = "Instarem"
    corridors = list(INSTAREM_LOCALE.keys())

    def __init__(self, send_amount=None, browser=None, **_kwargs) -> None:
        super().__init__(send_amount=send_amount, browser=browser)
        self.session.headers.update(
            {
                "Origin": "https://www.instarem.com",
                "Referer": "https://www.instarem.com/",
            }
        )

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        country_code = INSTAREM_COUNTRY.get(from_currency)
        if not country_code:
            raise ValueError(f"Unsupported corridor: {from_currency}")

        fee_resp = self._get_json(
            FEE_URL,
            params={
                "source_currency": from_currency,
                "source_amount": int(self.send_amount),
                "destination_currency": "NPR",
                "country_code": country_code,
            },
        )
        methods = fee_resp.get("data", [])
        if not methods:
            raise ValueError(f"No Instarem payment methods for {from_currency}")

        bank_id = methods[0]["key"]
        data = self._get_json(
            COMPUTED_URL,
            params={
                "source_currency": from_currency,
                "destination_currency": "NPR",
                "instarem_bank_account_id": bank_id,
                "country_code": country_code,
                "source_amount": int(self.send_amount),
            },
        )
        cfg = data["data"]["transaction_config"]
        rate = float(cfg["fx_rate"])
        fee = float(cfg.get("total_fee_amount") or 0)

        if fee == 0 and cfg.get("regular_total_fee_amount"):
            base_amount = float(cfg.get("from_currency_amount") or 100)
            fee = float(cfg["regular_total_fee_amount"]) * (self.send_amount / base_amount)
            discount = cfg.get("first_transaction_fee_config", {}).get(
                "discount_percentage", 0
            )
            if discount == 100:
                fee = 0.0

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=round(fee, 2),
            transfer_speed="Same day - 2 days",
            delivery_method="Bank transfer",
        )
