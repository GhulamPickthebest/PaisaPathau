"""Xoom (PayPal) quote via Wise comparisons aggregator."""

from __future__ import annotations

from constants import XOOM_LOCALE, active_corridors
from tier_b.calculator_api import CalculatorApiScraper
from tier_b.wise_comparison import fetch_comparison_quote
from tier_b.wise_transfer import _format_delivery


class XoomScraper(CalculatorApiScraper):
    provider_name = "Xoom (PayPal)"
    corridors = active_corridors(XOOM_LOCALE)

    def fetch_corridor(self, from_currency: str):
        quote = fetch_comparison_quote(
            "xoom",
            from_currency,
            send_amount=self.send_amount,
        )
        speed = _format_delivery(quote.get("delivery") or {}) or "Minutes to 3 business days"
        return self._build_record(
            from_currency=from_currency,
            exchange_rate=quote["rate"],
            fee=quote["fee"],
            receive_amount=quote["receive_amount"],
            transfer_speed=speed,
            delivery_method="Bank transfer",
        )
