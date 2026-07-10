"""Wise transfer quote via the same v3 quotes API the website calculator uses."""

from __future__ import annotations

from typing import Any

import requests

from utils import retry

WISE_QUOTES_V3 = "https://wise.com/gateway/v3/quotes"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://wise.com",
    "Referer": "https://wise.com/",
}


@retry(exceptions=(requests.RequestException, ValueError, KeyError))
def fetch_wise_transfer_quote(
    source_currency: str,
    target_currency: str = "NPR",
    send_amount: float = 1000.0,
    pay_in: str = "BANK_TRANSFER",
) -> dict[str, Any]:
    """Return Wise bank-transfer quote (rate, fee, receive) from gateway v3."""
    response = requests.post(
        WISE_QUOTES_V3,
        json={
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sourceAmount": send_amount,
        },
        headers=HEADERS,
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    rate = float(data.get("rate") or 0)
    if not rate:
        raise ValueError(f"Wise v3 quote missing rate for {source_currency}/{target_currency}")

    option = next(
        (
            item
            for item in data.get("paymentOptions", [])
            if item.get("payIn") == pay_in and item.get("payOut") == "BANK_TRANSFER"
        ),
        None,
    )
    if not option:
        raise ValueError(
            f"Wise v3 quote missing {pay_in} payment option for {source_currency}/{target_currency}"
        )

    fee_block = option.get("fee") or {}
    fee = float(fee_block.get("total") or fee_block.get("transferwise") or 0)
    receive = float(option.get("targetAmount") or 0)
    if not receive and rate:
        receive = round((send_amount - fee) * rate, 2)

    return {
        "rate": rate,
        "fee": fee,
        "receive_amount": receive,
        "delivery": option.get("formattedEstimatedDelivery") or "",
        "rate_timestamp": data.get("rateTimestamp"),
        "source": "wise_v3_quotes",
    }
