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


def parse_instarem_computed_payload(
    payload: dict,
    send_amount: float,
) -> dict[str, float]:
    """Extract customer-facing rates from Instarem computed-value response.

    Instarem exposes both ``fx_rate`` (reference) and ``instarem_fx_rate`` (applied
    on the website). We use the applied rates so exchange_rate matches destination_amount.
    """
    cfg = payload.get("transaction_config") or {}

    def _rate(*keys: str, fallback: float | None = None) -> float:
        for key in keys:
            raw = payload.get(key)
            if raw is None:
                raw = cfg.get(key)
            if raw is not None:
                return float(raw)
        if fallback is not None:
            return fallback
        raise ValueError("Instarem response missing FX rate fields")

    new_rate = _rate("instarem_fx_rate", "fx_rate")
    existing_rate = _rate(
        "regular_instarem_fx_rate",
        "instarem_fx_rate",
        "fx_rate",
        fallback=new_rate,
    )
    new_fee = float(payload.get("transaction_fee_amount") or 0)
    existing_fee = float(payload.get("regular_transaction_fee_amount") or 0)
    new_receive = float(payload.get("destination_amount") or 0)
    if not new_receive:
        new_receive = round((send_amount - new_fee) * new_rate, 2)
    existing_receive = round((send_amount - existing_fee) * existing_rate, 2)
    return {
        "new_rate": new_rate,
        "existing_rate": existing_rate,
        "new_fee": new_fee,
        "existing_fee": existing_fee,
        "new_receive": new_receive,
        "existing_receive": existing_receive,
    }


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
        parsed = parse_instarem_computed_payload(payload, self.send_amount)
        new_rate = parsed["new_rate"]
        existing_rate = parsed["existing_rate"]
        new_fee = parsed["new_fee"]
        existing_fee = parsed["existing_fee"]
        new_receive = parsed["new_receive"]
        existing_receive = parsed["existing_receive"]

        common = {
            "from_currency": from_currency,
            "transfer_speed": "Same day - 2 days",
            "delivery_method": "Bank transfer",
        }

        records = [
            self._build_record(
                **common,
                exchange_rate=new_rate,
                fee=round(new_fee, 2),
                receive_amount=new_receive,
                customer_type="new_user",
                rate_label="New User",
            )
        ]

        if existing_fee != new_fee or payload.get("first_instarem_transaction"):
            records.append(
                self._build_record(
                    **common,
                    exchange_rate=existing_rate,
                    fee=round(existing_fee, 2),
                    receive_amount=existing_receive,
                    customer_type="existing_user",
                    rate_label="Existing User",
                )
            )

        return records
