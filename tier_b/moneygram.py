"""MoneyGram — browser scrape + fee-quote API with session cookies."""

from __future__ import annotations

import json
import re
from typing import Any

from constants import MONEYGRAM_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from tier_b.browser_context import AU_CONTEXT
from tier_b.browser_helpers import dismiss_cookie_banners, parse_aud_npr_rate
from utils import retry

MONEYGRAM_NEPAL_URL = "https://www.moneygram.com/au/en/corridor/nepal"
FEE_QUOTE_URL = (
    "https://consumerapi.moneygram.com/services/capi/api/v1/sendMoney/feeQuote/v2"
    "?senderCountry=AUS&receiveCountry=NPL&senderCurrency=AUD"
    "&receiveCurrency=NPR&sendAmount={amount}&deliveryOption=BANK_DEPOSIT"
)


class MoneyGramScraper(BaseBrowserScraper):
    provider_name = "MoneyGram"
    corridors = active_corridors(MONEYGRAM_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency != "AUD":
            raise ValueError("MoneyGram browser scraper only supports AUD")

        quote: dict[str, Any] | None = None

        with self.page_context(context_options=AU_CONTEXT) as page:
            captured: list[dict[str, Any]] = []

            def on_response(response) -> None:
                if response.status != 200:
                    return
                url = response.url
                if "feeQuote" not in url and "fee-quote" not in url:
                    return
                try:
                    captured.append(response.json())
                except Exception:
                    pass

            page.on("response", on_response)
            page.goto(MONEYGRAM_NEPAL_URL, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(4000)
            dismiss_cookie_banners(page)

            quote = self._fetch_fee_quote(page, int(self.send_amount))
            if not quote and captured:
                quote = captured[-1]

            if not quote:
                body = page.inner_text("body")
                rate = parse_aud_npr_rate(body)
                if rate:
                    receive = round(self.send_amount * rate, 2)
                    return self._build_record(
                        from_currency=from_currency,
                        exchange_rate=rate,
                        fee=0.0,
                        receive_amount=receive,
                        transfer_speed="Minutes to 3 business days",
                        delivery_method="Bank / Cash pickup",
                    )
                raise ValueError("MoneyGram fee quote blocked (captcha/auth required)")

        return self._record_from_quote(quote, from_currency)

    def _fetch_fee_quote(self, page, amount: int) -> dict[str, Any] | None:
        result = page.evaluate(
            """async (url) => {
                const response = await fetch(url, { credentials: 'include' });
                const text = await response.text();
                return { status: response.status, text };
            }""",
            FEE_QUOTE_URL.format(amount=amount),
        )
        if result.get("status") != 200:
            return None
        try:
            return json.loads(result["text"])
        except json.JSONDecodeError:
            return None

    def _record_from_quote(self, quote: dict[str, Any], from_currency: str) -> RateRecord:
        fee_info = quote.get("feeQuote") or quote.get("data") or quote
        if isinstance(fee_info, dict) and "feeQuote" in fee_info:
            fee_info = fee_info["feeQuote"]

        rate = _dig_float(
            fee_info,
            "fxRate",
            "exchangeRate",
            "sendExchangeRate",
            "indicativeRate",
        )
        fee = _dig_float(fee_info, "sendFee", "fee", "totalSendFee", "transferFee") or 0.0
        receive = _dig_float(
            fee_info,
            "receiveAmount",
            "totalReceiveAmount",
            "totalAmountToCollect",
        )
        send = _dig_float(fee_info, "sendAmount", "totalSendAmount") or self.send_amount

        if not rate and receive and send:
            rate = receive / send
        if not rate or not receive:
            raise ValueError(f"Could not parse MoneyGram quote: {str(quote)[:300]}")

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=fee,
            receive_amount=receive,
            transfer_speed="Minutes to 3 business days",
            delivery_method="Bank / Cash pickup",
        )


def _dig_float(data: Any, *keys: str) -> float | None:
    if not isinstance(data, dict):
        return None
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, dict):
            nested = value.get("value") or value.get("amount")
            if nested is not None:
                return float(nested)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
