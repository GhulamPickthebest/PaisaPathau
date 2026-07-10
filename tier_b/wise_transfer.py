"""Wise remittance quote via gateway v3 (same source as wise.com calculator)."""

from __future__ import annotations

from constants import WISE_TRANSFER_LOCALE, active_corridors
from models import RateRecord
from tier_b.calculator_api import CalculatorApiScraper
from tier_b.wise_quotes import fetch_wise_transfer_quote


class WiseTransferScraper(CalculatorApiScraper):
    provider_name = "Wise"
    corridors = active_corridors(WISE_TRANSFER_LOCALE)
    source_label = "wise_v3_quotes"

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        quote = fetch_wise_transfer_quote(
            from_currency,
            send_amount=self.send_amount,
        )
        speed = quote.get("delivery") or "1-2 business days"

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=float(quote["rate"]),
            fee=float(quote["fee"]),
            receive_amount=float(quote["receive_amount"]),
            transfer_speed=speed,
            delivery_method="Bank transfer",
        )
