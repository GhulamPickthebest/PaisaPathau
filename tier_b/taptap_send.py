"""Taptap Send — capture fxRates from website (AU→NPR)."""

from __future__ import annotations

from typing import Any

from constants import TAPTAP_LOCALE, active_corridors
from models import RateRecord
from tier_b.base import BaseBrowserScraper
from tier_b.browser_context import AU_CONTEXT
from utils import retry

TAPTAP_NEPAL_URL = "https://www.taptapsend.com/en/send-money-to/nepal"
FX_RATES_URL = "https://api.taptapsend.com/api/fxRates"


class TaptapSendScraper(BaseBrowserScraper):
    provider_name = "Taptap Send"
    corridors = active_corridors(TAPTAP_LOCALE)

    @retry(exceptions=(Exception,))
    def fetch_corridor(self, from_currency: str) -> RateRecord:
        if from_currency != "AUD":
            raise ValueError("Taptap Send browser scraper only supports AUD")

        fx_payload: dict[str, Any] | None = None

        with self.page_context(context_options=AU_CONTEXT) as page:
            def on_response(response) -> None:
                nonlocal fx_payload
                if FX_RATES_URL in response.url and response.status == 200:
                    try:
                        fx_payload = response.json()
                    except Exception:
                        pass

            page.on("response", on_response)
            page.goto(TAPTAP_NEPAL_URL, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(6000)

            if not fx_payload:
                fx_payload = page.evaluate(
                    """async (url) => {
                        const r = await fetch(url, { credentials: 'include' });
                        if (!r.ok) return null;
                        return r.json();
                    }""",
                    FX_RATES_URL,
                )

        rate = _aud_npr_rate(fx_payload)
        fee = 0.0
        receive = round((self.send_amount - fee) * rate, 2)

        return self._build_record(
            from_currency=from_currency,
            exchange_rate=rate,
            fee=fee,
            receive_amount=receive,
            transfer_speed="Minutes to 1 business day",
            delivery_method="Bank / Cash pickup (City Express)",
        )


def _aud_npr_rate(payload: dict[str, Any] | None) -> float:
    if not payload:
        raise ValueError("Taptap fxRates response not captured")
    for country in payload.get("availableCountries", []):
        if country.get("isoCountryCode") != "AU":
            continue
        for corridor in country.get("corridors", []):
            if corridor.get("isoCountryCode") == "NP":
                rate = float(corridor.get("fxRate") or 0)
                if rate > 0:
                    return rate
    raise ValueError("AUD→NPR corridor not found in Taptap fxRates")
