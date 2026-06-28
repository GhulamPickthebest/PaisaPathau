"""Western Union quote via Wise comparisons API (AUD→NPR)."""

from __future__ import annotations

from constants import WU_LOCALE, active_corridors
from tier_b.calculator_api import CalculatorApiScraper
from tier_b.wise_comparison import fetch_comparison_quote
from tier_b.wise_transfer import _format_delivery

WU_COMPARISON_ALIAS = "western-union"


class WesternUnionApiScraper(CalculatorApiScraper):
    provider_name = "Western Union"
    corridors = active_corridors(WU_LOCALE)
    source_label = "wise_comparison"

    def fetch_corridor(self, from_currency: str):
        quote = fetch_comparison_quote(
            WU_COMPARISON_ALIAS,
            from_currency,
            send_amount=self.send_amount,
        )
        speed = (
            _format_delivery(quote.get("delivery") or {})
            or "Minutes to 3 business days"
        )
        return self._build_record(
            from_currency=from_currency,
            exchange_rate=quote["rate"],
            fee=quote["fee"],
            receive_amount=quote["receive_amount"],
            transfer_speed=speed,
            delivery_method="Bank transfer",
        )
