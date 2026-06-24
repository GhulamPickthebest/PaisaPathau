"""Ria Money Transfer — browser session + public calculator API."""

from __future__ import annotations

import json
from typing import Any

from constants import RIA_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from tier_b.browser_context import AU_CONTEXT
from utils import retry

RIA_NEPAL_URL = "https://www.riamoneytransfer.com/en-au/send-money-to-nepal"
CALCULATE_URL = "https://public.riamoneytransfer.com/MoneyTransferCalculator/Calculate"


class RiaScraper(BaseBrowserScraper):
    provider_name = "Ria Money Transfer"
    corridors = active_corridors(RIA_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency != "AUD":
            raise ValueError(f"Ria browser scraper only supports AUD (got {from_currency})")

        captured: dict[str, Any] | None = None

        with self.page_context(context_options=AU_CONTEXT) as page:
            def on_response(response) -> None:
                nonlocal captured
                if CALCULATE_URL in response.url and response.status == 200:
                    try:
                        payload = response.json()
                        selections = (
                            payload.get("model", {})
                            .get("transferDetails", {})
                            .get("selections", {})
                        )
                        if selections.get("currencyTo") == "NPR":
                            captured = payload
                    except (json.JSONDecodeError, ValueError):
                        pass

            page.on("response", on_response)
            page.goto(RIA_NEPAL_URL, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(4000)

            amount_input = page.locator(
                "#amount-from, input[name='amount-from'], [data-testid='amount-from']"
            ).first
            if amount_input.count():
                amount_input.click(click_count=3)
                amount_input.fill(str(int(self.send_amount)))
                page.keyboard.press("Tab")
                page.wait_for_timeout(5000)

            if not captured:
                captured = self._post_calculate(page)

        if not captured:
            raise ValueError("Ria calculator did not return NPR quote")

        calc = (
            captured.get("model", {})
            .get("transferDetails", {})
            .get("calculations", {})
        )
        rate = float(calc.get("exchangeRate") or 0)
        fee = float(calc.get("transferFee") or 0)
        receive = float(calc.get("amountTo") or 0)
        if rate <= 0 or receive <= 0:
            raise ValueError("Invalid Ria calculator response")

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=fee,
            receive_amount=receive,
            transfer_speed="Minutes to 4 business days",
            delivery_method="Bank / Cash pickup / Mobile wallet",
        )

    def _post_calculate(self, page) -> dict[str, Any] | None:
        """Call calculator API using browser cookies + anonymous session JWT."""
        return page.evaluate(
            """async ({ url, amount }) => {
                const session = await fetch(
                    'https://public.riamoneytransfer.com/Authorization/session',
                    { credentials: 'include' }
                );
                const sessionData = await session.json();
                const token = sessionData?.authToken?.jwtToken;
                const body = {
                    Amount: amount,
                    AmountType: 'SendAmount',
                    CountryFrom: 'AU',
                    CountryTo: 'NP',
                    CurrencyFrom: 'AUD',
                    CurrencyTo: 'NPR',
                    DeliveryMethod: '2',
                };
                const resp = await fetch(url, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? { Authorization: 'Bearer ' + token } : {}),
                    },
                    body: JSON.stringify(body),
                });
                if (!resp.ok) return null;
                return resp.json();
            }""",
            {"url": CALCULATE_URL, "amount": int(self.send_amount)},
        )
