"""Fetch per-method transfer matrix for AUD -> NPR."""

from __future__ import annotations

import requests
from urllib.parse import quote

from config import settings
from constants import (
    PROVIDER_TRANSFER_SPEEDS,
    REMITLY_PAYOUT_METHODS,
    STANDARD_TRANSFER_METHODS,
    WORLDREMIT_PAYOUT_METHODS,
)
from models import TransferMethodRow, utc_now_iso
from tier_b.western_union import WesternUnionScraper
from tier_b.worldremit import CREATE_CALCULATION, WORLDREMIT_COUNTRY
from utils import logger

REMITLY_API = "https://api.remitly.io/v3/calculator/estimate"
WORLDREMIT_GQL = "https://api.worldremit.com/graphql"
INSTAREM_FEE_URL = "https://www.instarem.com/api/v1/public/payment-method/fee"
INSTAREM_COMPUTED_URL = "https://www.instarem.com/api/v1/public/transaction/computed-value"
WISE_COMPARISONS = "https://wise.com/gateway/v4/comparisons"

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

    for fetcher in (
        _fetch_remitly_rows,
        _fetch_worldremit_rows,
        _fetch_instarem_rows,
        _fetch_wise_rows,
    ):
        try:
            rows.extend(fetcher(amount))
        except Exception as exc:
            msg = f"{fetcher.__name__}: {exc}"
            logger.error("AUD/NPR transfer methods: %s", msg)
            errors.append(msg)

    if not skip_browser:
        try:
            rows.extend(_fetch_western_union_rows(amount))
        except Exception as exc:
            msg = f"western_union: {exc}"
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


def _scale_existing(new_rate: float, ref_new: float, ref_existing: float) -> float | None:
    if ref_new <= 0 or ref_existing <= 0:
        return None
    return round(new_rate * (ref_existing / ref_new), 6)


def _fetch_remitly_rows(amount: float) -> list[TransferMethodRow]:
    conduit = quote("AUS:AUD-NPL:NPR", safe="")
    url = (
        f"{REMITLY_API}?conduit={conduit}&anchor=SEND&amount={int(amount)}"
        f"&purpose=OTHER&customer_segment=STANDARD"
        f"&customer_recognition=UNRECOGNIZED&strict_promo=false"
    )
    response = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    data = response.json()

    fastest, slowest = _speeds("Remitly")
    rows: list[TransferMethodRow] = []
    seen_methods: set[str] = set()

    def add_row(method_key: str, estimate: dict) -> None:
        label = REMITLY_PAYOUT_METHODS.get(method_key)
        if not label or label in seen_methods:
            return
        seen_methods.add(label)
        rate_data = estimate.get("exchange_rate", {})
        promo = float(rate_data.get("promotional_exchange_rate") or 0)
        base = float(rate_data.get("base_rate") or 0)
        fee = float(estimate.get("fee", {}).get("total_fee_amount") or 0)
        receive = float(estimate.get("receive_amount") or 0)
        rows.append(
            TransferMethodRow(
                provider="Remitly",
                transfer_method=label,
                fee=fee,
                new_user_rate=promo or None,
                existing_user_rate=base or None,
                min_amount=None,
                max_amount=None,
                fastest_speed=fastest,
                slowest_speed=slowest,
                send_amount=amount,
                receive_amount_new=receive if promo else None,
                receive_amount_existing=round(amount * base, 2) if base else None,
            )
        )

    add_row(data["estimate"]["pay_out_method"], data["estimate"])
    for estimate in data.get("pay_out_price_estimates", {}).get("estimates", []):
        add_row(estimate.get("pay_out_method", ""), estimate)

    logger.info("Remitly AUD/NPR transfer methods: %s rows", len(rows))
    return rows


def _fetch_worldremit_rows(amount: float) -> list[TransferMethodRow]:
    fastest, slowest = _speeds("WorldRemit")
    rows: list[TransferMethodRow] = []
    bnk_new = bnk_existing = 0.0

    for code, label in WORLDREMIT_PAYOUT_METHODS.items():
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
            continue

        calc = body.get("data", {}).get("createCalculation", {}).get("calculation")
        if not calc:
            continue

        send_value = float(calc["send"]["amount"])
        receive_value = float(calc["receive"]["amount"])
        fee = float(calc["informativeSummary"]["fee"]["value"]["amount"])
        exchange = calc["exchangeRate"]
        new_rate = receive_value / send_value
        promo_listed = float(exchange["value"])
        existing_listed = float(exchange.get("crossedOutValue") or 0)

        if code == "BNK":
            bnk_new = promo_listed
            bnk_existing = existing_listed

        existing_rate = existing_listed or None
        if not existing_rate and bnk_new and bnk_existing:
            existing_rate = _scale_existing(new_rate, bnk_new, bnk_existing)

        existing_receive = (
            round(amount * existing_rate, 2) if existing_rate else None
        )

        rows.append(
            TransferMethodRow(
                provider="WorldRemit",
                transfer_method=label,
                fee=fee,
                new_user_rate=round(new_rate, 6),
                existing_user_rate=existing_rate,
                min_amount=None,
                max_amount=None,
                fastest_speed=fastest,
                slowest_speed=slowest,
                send_amount=amount,
                receive_amount_new=receive_value,
                receive_amount_existing=existing_receive,
                notes="" if existing_listed else "Existing rate estimated from bank ratio",
            )
        )

    logger.info("WorldRemit AUD/NPR transfer methods: %s rows", len(rows))
    return rows


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
    rate = float(payload["fx_rate"])
    new_fee = float(payload.get("transaction_fee_amount") or 0)
    existing_fee = float(payload.get("regular_transaction_fee_amount") or 0)
    new_receive = float(payload.get("destination_amount") or 0)
    existing_receive = round((amount - existing_fee) * rate, 2)
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
            new_user_rate=rate,
            existing_user_rate=rate,
            min_amount=min_amount,
            max_amount=max_amount,
            fastest_speed=fastest,
            slowest_speed=slowest,
            send_amount=amount,
            receive_amount_new=new_receive,
            receive_amount_existing=existing_receive,
            notes="Same FX rate; existing user pays regular fee",
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
            notes="Single public rate; no new/existing split",
        )
    ]


def _fetch_western_union_rows(amount: float) -> list[TransferMethodRow]:
    scraper = WesternUnionScraper(send_amount=amount)
    records = scraper.fetch_corridor_records("AUD")
    by_type = {r.customer_type: r for r in records if r.status == "ok"}
    new_rec = by_type.get("new_user")
    existing_rec = by_type.get("existing_user")
    if not new_rec:
        raise ValueError("Western Union AUD quote unavailable")

    fastest, slowest = _speeds("Western Union")
    methods = ["Bank Transfer", "Cash Pickup", "Mobile Money Transfer"]
    rows: list[TransferMethodRow] = []
    for label in methods:
        rows.append(
            TransferMethodRow(
                provider="Western Union",
                transfer_method=label,
                fee=new_rec.fee,
                new_user_rate=new_rec.exchange_rate,
                existing_user_rate=existing_rec.exchange_rate if existing_rec else None,
                min_amount=None,
                max_amount=None,
                fastest_speed=fastest,
                slowest_speed=slowest,
                send_amount=amount,
                receive_amount_new=new_rec.receive_amount,
                receive_amount_existing=existing_rec.receive_amount if existing_rec else None,
                notes="Public calculator rate; same quote shown for bank/cash/mobile on landing page",
            )
        )
    logger.info("Western Union AUD/NPR transfer methods: %s rows", len(rows))
    return rows


def _unavailable_rows(existing: list[TransferMethodRow], amount: float) -> list[TransferMethodRow]:
    """Fill missing provider/method combos as unavailable."""
    covered = {(r.provider, r.transfer_method) for r in existing if r.status == "ok"}
    providers = ["Remitly", "WorldRemit", "Instarem", "Western Union", "Wise"]
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
                    notes="Not offered or not exposed via public API",
                )
            )
    return rows


def _format_iso_duration(value: str | None) -> str:
    if not value:
        return ""
    if value.startswith("PT") and "M" in value:
        minutes = value.replace("PT", "").split("M")[0].split("H")
        if len(minutes) == 2:
            return f"{minutes[0]}h {minutes[1]}m"
        return f"{minutes[0]} minutes"
    return value
