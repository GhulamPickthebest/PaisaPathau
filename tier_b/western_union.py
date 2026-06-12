"""Western Union scraper using embedded landing-page calculator."""

from __future__ import annotations

import re

from constants import WU_LOCALE
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError, retry

# Only corridors with an embedded send-money-to-nepal calculator widget.
WU_CALCULATOR_CORRIDORS = {"AUD"}


class WesternUnionScraper(BaseBrowserScraper):
    provider_name = "Western Union"
    corridors = list(WU_LOCALE.keys())

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency not in WU_CALCULATOR_CORRIDORS:
            raise PermanentScraperError(
                f"WU calculator widget not available for {from_currency}"
            )
        locale = WU_LOCALE[from_currency]
        url = f"https://www.westernunion.com/{locale}/en/send-money-to-nepal.html"

        with self.page_context() as page:
            page.goto(url, wait_until="commit", timeout=self.timeout)
            page.wait_for_timeout(8000)

            send_input = page.locator(f"#sender-amount-{from_currency}")
            if not send_input.count():
                raise ValueError(f"Calculator widget not available for {from_currency}")

            send_input.click(click_count=3)
            send_input.press("Backspace")
            send_input.type(str(int(self.send_amount)), delay=30)
            page.keyboard.press("Tab")
            page.wait_for_timeout(8000)

            receive_input = page.locator(
                'input[id*="receiver" i][id*="NPR" i], '
                'input[name*="receiver" i], '
                'input[id*="receiver-newcustomer" i]'
            ).first
            if not receive_input.count():
                raise ValueError(f"Receive amount field not found for {from_currency}")

            send_value = float(send_input.input_value())
            receive_value = float(receive_input.input_value())
            if send_value <= 0 or receive_value <= 0:
                raise ValueError("Invalid send/receive amounts from WU calculator")

            rate = receive_value / send_value
            fee = self._parse_wu_fee(page, from_currency)

            return self._build_record(
                from_currency=from_currency,
                exchange_rate=rate,
                fee=fee,
                receive_amount=receive_value,
                transfer_speed="Minutes to days",
                delivery_method="Bank / Cash pickup / Mobile wallet",
            )

    def _parse_wu_fee(self, page, from_currency: str) -> float:
        body = page.inner_text("body")
        patterns = [
            rf"transfer fee\*?\s*{from_currency}\s*([\d,.]+)",
            rf"fee\*?\s*{from_currency}\s*([\d,.]+)",
            r"\$0 transfer fee",
        ]
        if re.search(r"\$0 transfer fee|0 AUD transfer fees|0 USD transfer fees", body, re.I):
            return 0.0
        for pattern in patterns:
            match = re.search(pattern, body, re.I)
            if match and match.groups():
                return float(match.group(1).replace(",", ""))
        return 0.0
