"""Fetch provider quotes from Wise public comparisons API."""

from __future__ import annotations

from typing import Any

import requests

from utils import retry

WISE_COMPARISONS = "https://wise.com/gateway/v4/comparisons"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0",
    "Accept": "application/json",
    "Origin": "https://wise.com",
    "Referer": "https://wise.com/",
}


def format_delivery_duration(duration: dict) -> str:
    min_d = duration.get("min") or ""
    max_d = duration.get("max") or ""
    if min_d and max_d and min_d != max_d:
        return f"{min_d} - {max_d}"
    return min_d or max_d or ""


@retry(exceptions=(requests.RequestException, ValueError, KeyError))
def fetch_comparison_quote(
    provider_alias: str,
    source_currency: str,
    target_currency: str = "NPR",
    send_amount: float = 1000.0,
) -> dict[str, Any]:
    """Return quote dict for *provider_alias* (e.g. xoom, wise, remitly)."""
    response = requests.get(
        WISE_COMPARISONS,
        params={
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sendAmount": send_amount,
        },
        headers=HEADERS,
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    provider = next(
        (p for p in data.get("providers", []) if p.get("alias") == provider_alias),
        None,
    )
    if not provider or not provider.get("quotes"):
        raise ValueError(
            f"{provider_alias} quote unavailable for {source_currency}/{target_currency}"
        )
    quote = provider["quotes"][0]
    return {
        "rate": float(quote["rate"]),
        "fee": float(quote.get("fee") or 0),
        "receive_amount": float(quote.get("receivedAmount") or 0),
        "source": "wise_comparison",
        "delivery": quote.get("deliveryEstimation", {}).get("duration") or {},
    }
