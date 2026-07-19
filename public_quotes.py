"""Consumer-ready public rates table: valid, deduplicated, freshness-aware."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config import settings
from utils import format_exchange_rate

# Not remittance checkout quotes — exclude from the public comparison table.
EXCLUDED_PUBLIC_PROVIDERS = frozenset(
    {
        "Wise (mid-market)",
        "ExchangeRate-API",
        "Open Exchange Rates",
    }
)

# Always-unavailable providers — admin/health only.
ADMIN_ONLY_PROVIDERS = frozenset(
    {
        "MoneyGram",
        "ACE Money Transfer",
        "LuLu Exchange",
        "Revolut",
    }
)

INSTAREM_BRAND_NOTE = (
    "Instarem and Instarem (by Nium) are separate consumer brands on the same "
    "Nium network; rates may match."
)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive(value: Any) -> bool:
    number = _as_float(value)
    return number is not None and number > 0


def _parse_iso(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def quote_age_seconds(timestamp: Any, *, now: datetime | None = None) -> int | None:
    parsed = _parse_iso(timestamp)
    if parsed is None:
        return None
    current = now or datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, int((current - parsed).total_seconds()))


def is_quote_expired(age_seconds: int | None) -> bool:
    if age_seconds is None:
        return False
    return age_seconds > settings.quote_expire_after_seconds


def is_quote_stale(age_seconds: int | None, *, is_fallback: bool = False) -> bool:
    if is_fallback:
        return True
    if age_seconds is None:
        return False
    return age_seconds > settings.quote_stale_after_seconds


def is_valid_public_quote(record: dict[str, Any]) -> bool:
    """status=ok and positive exchange rate and receive amount."""
    if record.get("status") != "ok":
        return False
    rate = (
        record.get("new_user_rate")
        if record.get("new_user_rate") is not None
        else record.get("exchange_rate", record.get("rate"))
    )
    receive = (
        record.get("receive_amount_new")
        if record.get("receive_amount_new") is not None
        else record.get("receive_amount")
    )
    return _positive(rate) and _positive(receive)


def _canonical_wise_score(record: dict[str, Any]) -> tuple[int, int, float]:
    """Prefer fee-inclusive Wise v3 checkout quotes over mid-market."""
    source = str(record.get("source") or "")
    fee = _as_float(record.get("fee")) or 0.0
    receive = _as_float(
        record.get("receive_amount_new")
        if record.get("receive_amount_new") is not None
        else record.get("receive_amount")
    ) or 0.0
    provider = str(record.get("provider") or "")
    if "mid-market" in provider.lower():
        return (0, 0, receive)
    fee_inclusive = 1 if fee > 0 else 0
    is_v3 = 1 if source == "wise_v3_quotes" or source == "transfer_methods" else 0
    # Rank by fee-inclusive first, then v3 source, then receive (checkout net).
    return (fee_inclusive, is_v3, receive)


def _dedupe_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("provider") or ""),
        str(row.get("payment_method") or row.get("transfer_method") or row.get("delivery_method") or ""),
        str(row.get("customer_type") or row.get("rate_label") or ""),
    )


def _quoted_at_for_matrix_row(row: dict[str, Any], matrix_updated: Any) -> str:
    return str(row.get("quoted_at") or matrix_updated or "")


def _row_from_matrix(row: dict[str, Any], matrix_updated: Any) -> dict[str, Any]:
    provider = str(row.get("provider") or "")
    receive = row.get("receive_amount_new")
    if not _positive(receive):
        receive = row.get("receive_amount_existing")
    quoted_at = _quoted_at_for_matrix_row(row, matrix_updated)
    age = quote_age_seconds(quoted_at)
    is_fallback = bool(row.get("is_fallback"))
    stale = is_quote_stale(age, is_fallback=is_fallback)
    brand_note = INSTAREM_BRAND_NOTE if provider.startswith("Instarem") else ""
    news_parts: list[str] = []
    if row.get("notes"):
        news_parts.append(str(row["notes"]))
    if is_fallback:
        news_parts.append("Fallback: last successful quote")
    if stale and not is_fallback:
        news_parts.append("Stale quote")
    if brand_note:
        news_parts.append(brand_note)
    existing = row.get("existing_user_rate")
    new_rate = row.get("new_user_rate")
    if existing and new_rate and existing != new_rate:
        news_parts.append(f"Existing user rate: {existing}")

    return {
        "provider": provider,
        "rate": new_rate,
        "exchange_rate": new_rate,
        "payment_method": row.get("transfer_method") or "Bank Transfer",
        "fee": row.get("fee"),
        "receive_amount": receive,
        "send_amount": row.get("send_amount"),
        "customer_type": "new_user" if new_rate else "",
        "rate_label": "New User" if row.get("new_user_rate") else "",
        "existing_user_rate": existing,
        "receive_amount_existing": row.get("receive_amount_existing"),
        "transfer_speed": row.get("fastest_speed") or "",
        "quoted_at": quoted_at,
        "quote_age_seconds": age,
        "is_fallback": is_fallback,
        "is_stale": stale,
        "quote_freshness": "fallback" if is_fallback else ("stale" if stale else "live"),
        "brand_note": brand_note,
        "news": " · ".join(news_parts),
        "status": "ok",
        "source": "transfer_methods",
    }


def _row_from_rate_record(record: dict[str, Any]) -> dict[str, Any]:
    provider = str(record.get("provider") or "")
    quoted_at = str(record.get("timestamp") or "")
    age = quote_age_seconds(quoted_at)
    is_fallback = bool(record.get("is_fallback"))
    stale = is_quote_stale(age, is_fallback=is_fallback)
    brand_note = INSTAREM_BRAND_NOTE if provider.startswith("Instarem") else ""
    news_parts: list[str] = []
    if record.get("rate_label"):
        news_parts.append(str(record["rate_label"]))
    if record.get("transfer_speed"):
        news_parts.append(str(record["transfer_speed"]))
    if is_fallback:
        news_parts.append("Fallback: last successful quote")
    if stale and not is_fallback:
        news_parts.append("Stale quote")
    if brand_note:
        news_parts.append(brand_note)

    return {
        "provider": provider,
        "rate": record.get("exchange_rate"),
        "exchange_rate": record.get("exchange_rate"),
        "payment_method": record.get("delivery_method") or "Bank Transfer",
        "fee": record.get("fee"),
        "receive_amount": record.get("receive_amount"),
        "send_amount": record.get("send_amount"),
        "customer_type": record.get("customer_type") or "",
        "rate_label": record.get("rate_label") or "",
        "existing_user_rate": None,
        "receive_amount_existing": None,
        "transfer_speed": record.get("transfer_speed") or "",
        "quoted_at": quoted_at,
        "quote_age_seconds": age,
        "is_fallback": is_fallback,
        "is_stale": stale,
        "quote_freshness": "fallback" if is_fallback else ("stale" if stale else "live"),
        "brand_note": brand_note,
        "news": " · ".join(news_parts),
        "status": "ok",
        "source": record.get("source") or "",
    }


def _pick_canonical_wise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wise_rows = [row for row in rows if row.get("provider") == "Wise"]
    others = [row for row in rows if row.get("provider") != "Wise"]
    if not wise_rows:
        return others
    # One canonical Wise bank-transfer checkout quote (fee-inclusive preferred).
    bankish = [
        row
        for row in wise_rows
        if "cash" not in str(row.get("payment_method") or "").lower()
    ]
    pool = bankish or wise_rows
    best = max(pool, key=_canonical_wise_score)
    return others + [best]


def build_public_table_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only current, valid, deduplicated rows for the website table."""
    matrix = payload.get("aud_npr_transfer_methods") or {}
    matrix_updated = matrix.get("last_updated")
    candidates: list[dict[str, Any]] = []

    for row in matrix.get("rows", []):
        provider = str(row.get("provider") or "")
        if provider in EXCLUDED_PUBLIC_PROVIDERS or provider in ADMIN_ONLY_PROVIDERS:
            continue
        if not is_valid_public_quote(row):
            continue
        public_row = _row_from_matrix(row, matrix_updated)
        age = public_row.get("quote_age_seconds")
        if is_quote_expired(age if isinstance(age, int) else None):
            continue
        candidates.append(public_row)

    matrix_providers = {row["provider"] for row in candidates}

    for record in payload.get("all_rates", []):
        provider = str(record.get("provider") or "")
        if provider in EXCLUDED_PUBLIC_PROVIDERS or provider in ADMIN_ONLY_PROVIDERS:
            continue
        if provider == "Wise (mid-market)":
            continue
        # Prefer transfer-method matrix for providers already covered.
        if provider in matrix_providers and provider not in (
            "Xe Money Transfer",
            "Ria Money Transfer",
            "Taptap Send",
            "Skrill",
            "Xoom (PayPal)",
        ):
            # Matrix already has Remitly/WorldRemit/Instarem/Wise/WU — skip all_rates dupes
            if provider in {
                "Wise",
                "Remitly",
                "WorldRemit",
                "Instarem",
                "Instarem (by Nium)",
                "Western Union",
            }:
                continue
        if not is_valid_public_quote(record):
            continue
        public_row = _row_from_rate_record(record)
        age = public_row.get("quote_age_seconds")
        if is_quote_expired(age if isinstance(age, int) else None):
            continue
        candidates.append(public_row)

    candidates = _pick_canonical_wise(candidates)

    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in candidates:
        key = _dedupe_key(row)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = row
            continue
        # Prefer live over fallback, then higher receive amount.
        existing_receive = _as_float(existing.get("receive_amount")) or 0.0
        new_receive = _as_float(row.get("receive_amount")) or 0.0
        existing_rank = (
            0 if existing.get("is_fallback") else 1,
            existing_receive,
        )
        new_rank = (
            0 if row.get("is_fallback") else 1,
            new_receive,
        )
        if new_rank >= existing_rank:
            deduped[key] = row

    rows = list(deduped.values())
    rows.sort(
        key=lambda item: (
            _as_float(item.get("receive_amount")) or 0.0,
            _as_float(item.get("rate")) or 0.0,
        ),
        reverse=True,
    )
    return rows


def build_public_rates_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows = build_public_table_rows(payload)
    return {
        "last_updated": payload.get("last_updated"),
        "send_amount": payload.get("send_amount"),
        "from_currency": "AUD",
        "to_currency": "NPR",
        "cached": payload.get("cached", True),
        "fetch_mode": "snapshot",
        "snapshot_age_seconds": payload.get("snapshot_age_seconds"),
        "snapshot_refresh_seconds": settings.live_api_cache_seconds,
        "quote_stale_after_seconds": settings.quote_stale_after_seconds,
        "quote_expire_after_seconds": settings.quote_expire_after_seconds,
        "row_count": len(rows),
        "rows": rows,
        "status": payload.get("status", "ok"),
        "canonical_rules": {
            "valid_only": "status=ok and exchange_rate>0 and receive_amount>0",
            "wise": "Fee-inclusive Wise gateway v3 checkout quote; mid-market excluded",
            "instarem": INSTAREM_BRAND_NOTE,
            "ranking": "Sorted by receive_amount descending",
            "freshness": (
                f"Marked stale after {settings.quote_stale_after_seconds}s; "
                f"excluded after {settings.quote_expire_after_seconds}s"
            ),
            "fallback": "Temporary failures keep last successful quote with is_fallback=true",
        },
    }


def build_admin_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    """Errors and invalid/unavailable rows for health/admin only."""
    errors = list(payload.get("errors") or [])
    unavailable: list[dict[str, Any]] = []
    for record in payload.get("all_rates", []):
        if record.get("status") == "error" or not is_valid_public_quote(record):
            if record.get("status") == "ok" and is_valid_public_quote(record):
                continue
            unavailable.append(
                {
                    "provider": record.get("provider"),
                    "status": record.get("status"),
                    "error_message": record.get("error_message")
                    or ("invalid quote" if record.get("status") == "ok" else "error"),
                    "timestamp": record.get("timestamp"),
                    "exchange_rate": record.get("exchange_rate"),
                    "receive_amount": record.get("receive_amount"),
                }
            )
    matrix = payload.get("aud_npr_transfer_methods") or {}
    for row in matrix.get("rows", []):
        if row.get("status") in ("unavailable", "error") or not is_valid_public_quote(row):
            if row.get("status") == "ok" and is_valid_public_quote(row):
                continue
            unavailable.append(
                {
                    "provider": row.get("provider"),
                    "transfer_method": row.get("transfer_method"),
                    "status": row.get("status"),
                    "notes": row.get("notes"),
                }
            )
    return {
        "errors": errors,
        "unavailable": unavailable,
        "last_updated": payload.get("last_updated"),
        "snapshot_age_seconds": payload.get("snapshot_age_seconds"),
        "refresh_kind": payload.get("refresh_kind"),
    }


def format_public_rate(value: Any) -> str:
    return format_exchange_rate(_as_float(value), places=3)
