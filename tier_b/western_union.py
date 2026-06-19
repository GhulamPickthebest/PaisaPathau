"""Western Union scraper using embedded landing-page calculator."""

from __future__ import annotations

import re

from constants import WU_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from utils import PermanentScraperError, retry

# Only corridors with an embedded send-money-to-nepal calculator widget.
WU_CALCULATOR_CORRIDORS = {"AUD"}

NEW_CUSTOMER_RECEIVE_INPUT = "#wu-input-price-receiver-newcustomer-gets-NPR"
PROMO_RECEIVE_PAIR_PATTERN = re.compile(
    r"receive\s+([\d,.]+)\s+([\d,.]+)\s*NPR",
    re.IGNORECASE,
)
PROMO_HTML_PAIR_PATTERN = re.compile(
    r"<strike>([\d,.]+)</strike>\s*<b>([\d,.]+)</b>",
    re.IGNORECASE,
)


class WesternUnionScraper(BaseBrowserScraper):
    provider_name = "Western Union"
    corridors = active_corridors(WU_LOCALE)

    def fetch_corridor(self, from_currency: str) -> RateRecord:
        return self.fetch_corridor_records(from_currency)[0]

    @retry(exceptions=(Exception,))
    def fetch_corridor_records(self, from_currency: str) -> list[RateRecord]:
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

            new_receive_input = page.locator(NEW_CUSTOMER_RECEIVE_INPUT)
            if not new_receive_input.count():
                raise ValueError(f"New customer receive field not found for {from_currency}")

            send_value = float(send_input.input_value())
            new_receive = float(new_receive_input.input_value())
            if send_value <= 0 or new_receive <= 0:
                raise ValueError("Invalid send/receive amounts from WU calculator")

            fee = self._parse_wu_fee(page, from_currency)
            new_rate = new_receive / send_value
            common = {
                "from_currency": from_currency,
                "fee": fee,
                "transfer_speed": "Minutes to days",
                "delivery_method": "Bank / Cash pickup / Mobile wallet",
            }

            records = [
                self._build_record(
                    **common,
                    exchange_rate=new_rate,
                    receive_amount=new_receive,
                    customer_type="new_user",
                    rate_label="New User",
                )
            ]

            promo_pair = self._parse_promo_receive_pair(page)
            if promo_pair:
                existing_ref, new_ref = promo_pair
                existing_receive = scale_existing_receive(
                    new_receive, existing_ref, new_ref
                )
                existing_rate = existing_receive / send_value
                records.append(
                    self._build_record(
                        **common,
                        exchange_rate=existing_rate,
                        receive_amount=existing_receive,
                        customer_type="existing_user",
                        rate_label="Existing User",
                    )
                )

            return records

    def _parse_promo_receive_pair(self, page) -> tuple[float, float] | None:
        """Parse (existing, new) receive amounts from the promo block."""
        html = page.content()
        html_match = PROMO_HTML_PAIR_PATTERN.search(html)
        if html_match:
            return _parse_amount(html_match.group(1)), _parse_amount(html_match.group(2))

        body = page.inner_text("body")
        text_match = PROMO_RECEIVE_PAIR_PATTERN.search(body)
        if text_match:
            return _parse_amount(text_match.group(1)), _parse_amount(text_match.group(2))

        return None

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


def _parse_amount(value: str) -> float:
    return float(value.replace(",", ""))


def scale_existing_receive(
    new_receive: float, existing_ref: float, new_ref: float
) -> float:
    """Scale promo-block existing receive to the current send amount."""
    if new_ref <= 0:
        raise ValueError("Invalid promo reference amounts from WU page")
    return round(new_receive * (existing_ref / new_ref), 2)
