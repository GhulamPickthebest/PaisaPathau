"""Instarem calculator API scraper."""

from __future__ import annotations

from constants import INSTAREM_LOCALE, active_corridors
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
    corridors = active_corridors(INSTAREM_LOCALE)

    def __init__(self, send_amount=None, browser=None, **_kwargs) -> None:
        super().__init__(send_amount=send_amount, browser=browser)
        self.session.headers.update(
            {
                "Origin": "https://www.instarem.com",
                "Referer": "https://www.instarem.com/",
            }
        )

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        return self.fetch_corridor_records(from_currency)[0]

    def fetch_corridor_records(self, from_currency: str) -> list[RateRecord]:
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
        payload = data["data"]
        cfg = payload["transaction_config"]
        rate = float(cfg["fx_rate"])
        new_fee = float(payload.get("transaction_fee_amount") or 0)
        existing_fee = float(payload.get("regular_transaction_fee_amount") or 0)
        new_receive = float(payload.get("destination_amount") or 0)

        common = {
            "from_currency": from_currency,
            "exchange_rate": rate,
            "transfer_speed": "Same day - 2 days",
            "delivery_method": "Bank transfer",
        }

        records = [
            self._build_record(
                **common,
                fee=round(new_fee, 2),
                receive_amount=new_receive,
                customer_type="new_user",
                rate_label="New User",
            )
        ]

        if existing_fee != new_fee or payload.get("first_instarem_transaction"):
            existing_receive = round((self.send_amount - existing_fee) * rate, 2)
            records.append(
                self._build_record(
                    **common,
                    fee=round(existing_fee, 2),
                    receive_amount=existing_receive,
                    customer_type="existing_user",
                    rate_label="Existing User",
                )
            )

        return records
