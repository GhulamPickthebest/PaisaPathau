"""Fetch per-method transfer matrix for AUD -> NPR."""

from __future__ import annotations

import re
from urllib.parse import quote

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import settings
from constants import (
    AUD_NPR_PROVIDERS,
    PROVIDER_TRANSFER_SPEEDS,
    REMITLY_PAYOUT_METHODS,
    STANDARD_TRANSFER_METHODS,
    WORLDREMIT_PAYOUT_METHODS,
    WORLDREMIT_WALLET_ALIAS_CODE,
)
from models import TransferMethodRow, utc_now_iso
from tier_b.instarem import parse_instarem_computed_payload
from tier_b.western_union_transfer_methods import WesternUnionTransferMethodsScraper
from tier_b.wise_comparison import fetch_comparison_quote
from tier_b.wise_transfer import _format_delivery
from tier_b.worldremit import CREATE_CALCULATION, WORLDREMIT_COUNTRY
from utils import logger

REMITLY_API = "https://api.remitly.io/v3/calculator/estimate"
WORLDREMIT_GQL = "https://api.worldremit.com/graphql"
INSTAREM_FEE_URL = "https://www.instarem.com/api/v1/public/payment-method/fee"
INSTAREM_COMPUTED_URL = "https://www.instarem.com/api/v1/public/transaction/computed-value"
WISE_COMPARISONS = "https://wise.com/gateway/v4/comparisons"

WORLDREMIT_PAY_OUT_METHODS_QUERY = """
query payOutMethods($payOutMethodsInput: PayOutMethodsInput!) {
  payOutMethods(payOutMethodsInput: $payOutMethodsInput) {
    code
    name
    description
    feeEstimate(sendCurrency: "AUD") { value { amount currency } }
    payOutTimeEstimate
  }
}
"""

WORLDREMIT_HEADERS = {
    "Origin": "https://www.worldremit.com",
    "Referer": "https://www.worldremit.com/",
    "X-WR-Platform": "WEB",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
}


def fetch_aud_npr_transfer_methods(
    send_amount: float | None = None,
    skip_browser: bool = False,
) -> dict:
    amount = send_amount or settings.send_amount
    rows: list[TransferMethodRow] = []
    errors: list[str] = []

    fetchers = [
        _fetch_remitly_rows,
        _fetch_worldremit_rows,
        _fetch_instarem_rows,
        _fetch_wise_rows,
    ]
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = {executor.submit(fn, amount): fn for fn in fetchers}
        for future in as_completed(futures):
            fn = futures[future]
            try:
                rows.extend(future.result())
            except Exception as exc:
                msg = f"{fn.__name__}: {exc}"
                logger.error("AUD/NPR transfer methods: %s", msg)
                errors.append(msg)

    if not skip_browser:
        try:
            rows.extend(_fetch_western_union_rows(amount))
        except Exception as exc:
            msg = f"western_union: {exc}"
            logger.error("AUD/NPR transfer methods: %s", msg)
            errors.append(msg)
    else:
        try:
            rows.extend(_fetch_western_union_comparison_rows(amount))
        except Exception as exc:
            msg = f"western_union_comparison: {exc}"
            logger.error("AUD/NPR transfer methods: %s", msg)
            errors.append(msg)

    rows.extend(_unavailable_rows(rows, amount))

    return {
        "last_updated": utc_now_iso(),
        "from_currency": "AUD",
        "to_currency": "NPR",
        "send_amount": amount,
        "transfer_methods": STANDARD_TRANSFER_METHODS,
        "rows": [row.to_dict() for row in rows],
        "errors": errors,
    }


def _speeds(provider: str) -> tuple[str, str]:
    speeds = PROVIDER_TRANSFER_SPEEDS.get(provider, {})
    return speeds.get("fastest", ""), speeds.get("slowest", "")


def _remitly_fetch(amount: float, strict_promo: bool) -> dict:
    conduit = quote("AUS:AUD-NPL:NPR", safe="")
    url = (
        f"{REMITLY_API}?conduit={conduit}&anchor=SEND&amount={int(amount)}"
        f"&purpose=OTHER&customer_segment=STANDARD"
        f"&customer_recognition=UNRECOGNIZED"
        f"&strict_promo={'true' if strict_promo else 'false'}"
    )
    response = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        raise ValueError(data[0].get("message", "Remitly API error"))
    return data


def _remitly_estimates_by_method(data: dict) -> dict[str, dict]:
    estimates: dict[str, dict] = {}
    all_estimates = [data["estimate"]] + data.get("pay_out_price_estimates", {}).get(
        "estimates", []
    )
    for estimate in all_estimates:
        method_key = estimate.get("pay_out_method", "")
        if method_key and method_key not in estimates:
            estimates[method_key] = estimate
    return estimates


def _fetch_remitly_rows(amount: float) -> list[TransferMethodRow]:
    """Two API calls: strict_promo=false (new user) + strict_promo=true (existing)."""
    new_data = _remitly_fetch(amount, strict_promo=False)
    existing_data = _remitly_fetch(amount, strict_promo=True)
    new_by_method = _remitly_estimates_by_method(new_data)
    existing_by_method = _remitly_estimates_by_method(existing_data)

    fastest, slowest = _speeds("Remitly")
    rows: list[TransferMethodRow] = []

    for method_key, label in REMITLY_PAYOUT_METHODS.items():
        new_est = new_by_method.get(method_key)
        existing_est = existing_by_method.get(method_key)
        if not new_est and not existing_est:
            continue

        new_rate_data = (new_est or {}).get("exchange_rate", {})
        existing_rate_data = (existing_est or new_est or {}).get("exchange_rate", {})
        new_rate = float(new_rate_data.get("promotional_exchange_rate") or 0) or None
        existing_rate = float(existing_rate_data.get("base_rate") or 0) or None
        new_fee = float((new_est or {}).get("fee", {}).get("total_fee_amount") or 0)
        existing_fee = float(
            (existing_est or {}).get("fee", {}).get("total_fee_amount") or 0
        )
        new_receive = float((new_est or {}).get("receive_amount") or 0) or None
        existing_receive = (
            float((existing_est or {}).get("receive_amount") or 0) or None
        )

        rows.append(
            TransferMethodRow(
                provider="Remitly",
                transfer_method=label,
                fee=new_fee,
                new_user_rate=new_rate,
                existing_user_rate=existing_rate,
                min_amount=None,
                max_amount=None,
                fastest_speed=fastest,
                slowest_speed=slowest,
                send_amount=amount,
                receive_amount_new=new_receive,
                receive_amount_existing=existing_receive,
                notes="Rates from Remitly calculator API (strict_promo new/existing calls)",
            )
        )

    logger.info("Remitly AUD/NPR transfer methods: %s rows", len(rows))
    return rows


def _worldremit_payout_metadata() -> dict[str, dict]:
    payload = {
        "operationName": "payOutMethods",
        "variables": {
            "payOutMethodsInput": {
                "sendCountry": "AU",
                "receiveCountry": "NP",
                "receiveCurrency": "NPR",
            }
        },
        "query": WORLDREMIT_PAY_OUT_METHODS_QUERY,
    }
    response = requests.post(
        WORLDREMIT_GQL, json=payload, headers=WORLDREMIT_HEADERS, timeout=25
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise ValueError(body["errors"][0].get("message", "WorldRemit payOutMethods error"))
    return {item["code"]: item for item in body["data"]["payOutMethods"]}


def _fetch_worldremit_rows(amount: float) -> list[TransferMethodRow]:
    metadata = _worldremit_payout_metadata()
    default_fastest, default_slowest = _speeds("WorldRemit")
    rows: list[TransferMethodRow] = []

    for code, label in WORLDREMIT_PAYOUT_METHODS.items():
        row = _worldremit_method_row(
            code, label, amount, metadata.get(code, {}), default_fastest, default_slowest
        )
        if row:
            rows.append(row)

    # Khalti wallet delivery (WorldRemit MOB) also maps to Wallet Transfer
    if WORLDREMIT_WALLET_ALIAS_CODE in metadata:
        wallet_row = _worldremit_method_row(
            WORLDREMIT_WALLET_ALIAS_CODE,
            "Wallet Transfer",
            amount,
            metadata[WORLDREMIT_WALLET_ALIAS_CODE],
            default_fastest,
            default_slowest,
            notes_prefix="Khalti wallet via WorldRemit MOB. ",
        )
        if wallet_row:
            rows.append(wallet_row)

    logger.info("WorldRemit AUD/NPR transfer methods: %s rows", len(rows))
    return rows


def _worldremit_method_row(
    code: str,
    label: str,
    amount: float,
    meta: dict,
    default_fastest: str,
    default_slowest: str,
    notes_prefix: str = "",
) -> TransferMethodRow | None:
    payload = {
        "operationName": "createCalculation",
        "variables": {
            "amount": int(amount),
            "type": "SEND",
            "sendCountryCode": WORLDREMIT_COUNTRY["AUD"],
            "sendCurrencyCode": "AUD",
            "receiveCountryCode": "NP",
            "receiveCurrencyCode": "NPR",
            "payOutMethodCode": code,
            "correspondentId": "",
        },
        "query": CREATE_CALCULATION,
    }
    response = requests.post(
        WORLDREMIT_GQL, json=payload, headers=WORLDREMIT_HEADERS, timeout=25
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        logger.warning("WorldRemit %s unavailable: %s", code, body["errors"][0].get("message"))
        return None

    calc = body.get("data", {}).get("createCalculation", {}).get("calculation")
    if not calc:
        return None

    send_value = float(calc["send"]["amount"])
    receive_value = float(calc["receive"]["amount"])
    fee = float(calc["informativeSummary"]["fee"]["value"]["amount"])
    exchange = calc["exchangeRate"]
    new_rate = round(receive_value / send_value, 6)
    existing_listed = float(exchange.get("crossedOutValue") or 0)

    if existing_listed:
        existing_rate = round(existing_listed, 6)
        existing_receive = round(amount * existing_rate, 2)
        note = f"{notes_prefix}Existing rate from API crossedOutValue"
    else:
        # No promo spread on this payout method — new and existing are the same rate
        existing_rate = new_rate
        existing_receive = receive_value
        note = f"{notes_prefix}No promotional spread on this payout method (same rate for all users)"

    fastest, slowest = _parse_worldremit_speed(meta.get("payOutTimeEstimate"))
    if not fastest:
        fastest, slowest = default_fastest, default_slowest

    meta_fee = _worldremit_meta_fee(meta)
    if meta_fee is not None and fee == 0 and meta_fee > 0:
        fee = meta_fee

    return TransferMethodRow(
        provider="WorldRemit",
        transfer_method=label,
        fee=fee,
        new_user_rate=new_rate,
        existing_user_rate=existing_rate,
        min_amount=None,
        max_amount=None,
        fastest_speed=fastest,
        slowest_speed=slowest,
        send_amount=amount,
        receive_amount_new=receive_value,
        receive_amount_existing=existing_receive,
        notes=note.strip(),
    )


def _worldremit_meta_fee(meta: dict) -> float | None:
    fee_estimate = meta.get("feeEstimate") or {}
    value = fee_estimate.get("value") or {}
    amount = value.get("amount")
    return float(amount) if amount is not None else None


def _parse_worldremit_speed(text: str | None) -> tuple[str, str]:
    if not text:
        return "", ""
    cleaned = re.sub(r"[^\w\s]", "", text).strip()
    if not cleaned:
        return "", ""
    # e.g. "Within 5 minutes" -> fastest and slowest same for WR public estimate
    return cleaned, cleaned


def _fetch_instarem_rows(amount: float) -> list[TransferMethodRow]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.instarem.com",
    }
    fee_resp = requests.get(
        INSTAREM_FEE_URL,
        params={
            "source_currency": "AUD",
            "source_amount": int(amount),
            "destination_currency": "NPR",
            "country_code": "AU",
        },
        headers=headers,
        timeout=25,
    )
    fee_resp.raise_for_status()
    methods = fee_resp.json().get("data", [])
    if not methods:
        raise ValueError("No Instarem payment methods for AUD/NPR")

    bank_id = methods[0]["key"]
    cv_resp = requests.get(
        INSTAREM_COMPUTED_URL,
        params={
            "source_currency": "AUD",
            "destination_currency": "NPR",
            "instarem_bank_account_id": bank_id,
            "country_code": "AU",
            "source_amount": int(amount),
        },
        headers=headers,
        timeout=25,
    )
    cv_resp.raise_for_status()
    payload = cv_resp.json()["data"]
    cfg = payload["transaction_config"]
    parsed = parse_instarem_computed_payload(payload, amount)
    new_rate = parsed["new_rate"]
    existing_rate = parsed["existing_rate"]
    new_fee = parsed["new_fee"]
    existing_fee = parsed["existing_fee"]
    new_receive = parsed["new_receive"]
    existing_receive = parsed["existing_receive"]
    min_amount = float(cfg.get("min_source_amount_limit") or 0) or None
    max_amount = float(cfg.get("max_source_amount_limit") or 0) or None
    if max_amount and max_amount > 1_000_000:
        max_amount = None

    fastest, slowest = _speeds("Instarem")
    return [
        TransferMethodRow(
            provider="Instarem",
            transfer_method="Bank Transfer",
            fee=new_fee,
            new_user_rate=new_rate,
            existing_user_rate=existing_rate,
            min_amount=min_amount,
            max_amount=max_amount,
            fastest_speed=fastest,
            slowest_speed=slowest,
            send_amount=amount,
            receive_amount_new=new_receive,
            receive_amount_existing=existing_receive,
            notes="Applied FX (instarem_fx_rate); existing user pays regular fee",
        )
    ]


def _fetch_wise_rows(amount: float) -> list[TransferMethodRow]:
    response = requests.get(
        WISE_COMPARISONS,
        params={
            "sourceCurrency": "AUD",
            "targetCurrency": "NPR",
            "sendAmount": amount,
        },
        timeout=25,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    data = response.json()
    wise = next(
        (p for p in data.get("providers", []) if p.get("alias") == "wise"),
        None,
    )
    if not wise or not wise.get("quotes"):
        raise ValueError("Wise comparison quote unavailable for AUD/NPR")

    quote = wise["quotes"][0]
    rate = float(quote["rate"])
    fee = float(quote.get("fee") or 0)
    receive = float(quote.get("receivedAmount") or 0)
    duration = quote.get("deliveryEstimation", {}).get("duration") or {}
    fastest = _format_iso_duration(duration.get("min")) or _speeds("Wise")[0]
    slowest = _format_iso_duration(duration.get("max")) or _speeds("Wise")[1]

    return [
        TransferMethodRow(
            provider="Wise",
            transfer_method="Bank Transfer",
            fee=fee,
            new_user_rate=rate,
            existing_user_rate=rate,
            min_amount=None,
            max_amount=None,
            fastest_speed=fastest,
            slowest_speed=slowest,
            send_amount=amount,
            receive_amount_new=receive,
            receive_amount_existing=receive,
            notes="Wise public transfer quote; no new/existing rate split on this endpoint",
        )
    ]


def _fetch_western_union_comparison_rows(amount: float) -> list[TransferMethodRow]:
    """Bank-transfer row from Wise comparisons when Playwright is skipped."""
    quote = fetch_comparison_quote("western-union", "AUD", send_amount=amount)
    rate = float(quote["rate"])
    fee = float(quote["fee"])
    receive = float(quote["receive_amount"])
    duration = quote.get("delivery") or {}
    fastest = _format_iso_duration(duration.get("min")) or _speeds("Western Union")[0]
    slowest = _format_iso_duration(duration.get("max")) or _speeds("Western Union")[1]

    return [
        TransferMethodRow(
            provider="Western Union",
            transfer_method="Bank Transfer",
            fee=fee,
            new_user_rate=rate,
            existing_user_rate=rate,
            min_amount=None,
            max_amount=None,
            fastest_speed=fastest,
            slowest_speed=slowest,
            send_amount=amount,
            receive_amount_new=receive,
            receive_amount_existing=receive,
            notes="Wise comparisons quote; enable skip_browser=false for per-method data",
        )
    ]


def _fetch_western_union_rows(amount: float) -> list[TransferMethodRow]:
    quotes = WesternUnionTransferMethodsScraper(send_amount=amount).fetch_method_quotes(
        amount
    )
    rows: list[TransferMethodRow] = []
    for quote in quotes:
        rows.append(
            TransferMethodRow(
                provider="Western Union",
                transfer_method=quote["transfer_method"],
                fee=quote["fee"],
                new_user_rate=quote["new_user_rate"],
                existing_user_rate=quote["existing_user_rate"],
                min_amount=None,
                max_amount=None,
                fastest_speed=quote["fastest_speed"],
                slowest_speed=quote["slowest_speed"],
                send_amount=amount,
                receive_amount_new=quote["receive_amount_new"],
                receive_amount_existing=quote["receive_amount_existing"],
                notes=quote["notes"],
            )
        )
    logger.info("Western Union AUD/NPR transfer methods: %s rows", len(rows))
    return rows


def _unavailable_rows(existing: list[TransferMethodRow], amount: float) -> list[TransferMethodRow]:
    covered = {(r.provider, r.transfer_method) for r in existing if r.status == "ok"}
    providers = list(AUD_NPR_PROVIDERS)
    rows: list[TransferMethodRow] = []

    for provider in providers:
        fastest, slowest = _speeds(provider)
        for method in STANDARD_TRANSFER_METHODS:
            if (provider, method) in covered:
                continue
            rows.append(
                TransferMethodRow(
                    provider=provider,
                    transfer_method=method,
                    fee=None,
                    new_user_rate=None,
                    existing_user_rate=None,
                    min_amount=None,
                    max_amount=None,
                    fastest_speed=fastest,
                    slowest_speed=slowest,
                    send_amount=amount,
                    status="unavailable",
                    notes="Not offered for AUD→NPR via public API",
                )
            )
    return rows


def _format_iso_duration(value: str | None) -> str:
    if not value:
        return ""
    if value.startswith("PT") and "M" in value:
        parts = value.replace("PT", "").split("M")[0].split("H")
        if len(parts) == 2:
            return f"{parts[0]}h {parts[1]}m"
        return f"{parts[0]} minutes"
    return value
