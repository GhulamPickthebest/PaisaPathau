"""Merge new fetch results with the last successful snapshot."""

from __future__ import annotations

from typing import Any

from models import utc_now_iso
from table_view import _has_valid_rate


def rate_record_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        record.get("provider", ""),
        record.get("from_currency", ""),
        record.get("customer_type", ""),
        record.get("rate_label", ""),
    )


def transfer_row_key(row: dict[str, Any]) -> tuple[str, str]:
    return (row.get("provider", ""), row.get("transfer_method", ""))


def _mark_live(record: dict[str, Any]) -> dict[str, Any]:
    live = dict(record)
    live["is_fallback"] = False
    live["quote_freshness"] = "live"
    return live


def _mark_fallback(record: dict[str, Any]) -> dict[str, Any]:
    kept = dict(record)
    kept["is_fallback"] = True
    kept["quote_freshness"] = "fallback"
    # Preserve original timestamp / quoted_at from the successful quote.
    return kept


def merge_rate_records(
    new_records: list[dict[str, Any]],
    previous_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep last successful quote when a provider fails on the next run.

    Error / zero-value rows are never kept in the merged main list when a
    previous successful quote exists for the same key.

    Quotes carried forward because they were not attempted this cycle
    (e.g. browser providers during an API-only refresh) keep their prior
    freshness flags — they are NOT marked as fallback.
    """
    previous_ok = {
        rate_record_key(record): record
        for record in previous_records
        if record.get("status") == "ok"
        and float(record.get("exchange_rate") or 0) > 0
        and float(record.get("receive_amount") or 0) > 0
    }
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for record in new_records:
        key = rate_record_key(record)
        seen.add(key)
        if (
            record.get("status") == "ok"
            and float(record.get("exchange_rate") or 0) > 0
            and float(record.get("receive_amount") or 0) > 0
        ):
            merged.append(_mark_live(record))
            continue
        if key in previous_ok:
            # Attempted this cycle but failed — true fallback.
            merged.append(_mark_fallback(previous_ok[key]))
            continue
        # No prior good quote — omit zero/error rows from the main rates list.

    for key, record in previous_ok.items():
        if key not in seen:
            # Not attempted this cycle — preserve as-is (no false fallback).
            merged.append(dict(record))

    return merged


def merge_transfer_rows(
    new_rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep last successful transfer-method row when the next fetch fails."""
    previous_ok = {
        transfer_row_key(row): row
        for row in previous_rows
        if row.get("status") == "ok" and _has_valid_rate(row)
    }
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for row in new_rows:
        key = transfer_row_key(row)
        seen.add(key)
        if row.get("status") == "ok" and _has_valid_rate(row):
            live = _mark_live(row)
            if not live.get("quoted_at"):
                live["quoted_at"] = utc_now_iso()
            merged.append(live)
            continue
        if key in previous_ok:
            merged.append(_mark_fallback(previous_ok[key]))
            continue

    for key, row in previous_ok.items():
        if key not in seen:
            merged.append(dict(row))

    return merged


def merge_payloads(
    new_payload: dict[str, Any],
    previous_payload: dict[str, Any] | None,
    refresh_seconds: int,
) -> dict[str, Any]:
    if not previous_payload:
        merged = dict(new_payload)
        matrix = dict(merged.get("aud_npr_transfer_methods") or {})
        if matrix:
            matrix.setdefault("last_updated", merged.get("last_updated") or utc_now_iso())
            for row in matrix.get("rows", []):
                if row.get("status") == "ok" and not row.get("quoted_at"):
                    row["quoted_at"] = matrix["last_updated"]
                if row.get("status") == "ok":
                    row["is_fallback"] = False
                    row["quote_freshness"] = "live"
            merged["aud_npr_transfer_methods"] = matrix
    else:
        merged = dict(new_payload)
        merged["all_rates"] = merge_rate_records(
            new_payload.get("all_rates", []),
            previous_payload.get("all_rates", []),
        )
        new_matrix = new_payload.get("aud_npr_transfer_methods") or {}
        prev_matrix = previous_payload.get("aud_npr_transfer_methods") or {}
        if new_matrix or prev_matrix:
            # New matrix metadata wins (including last_updated).
            matrix = {
                **prev_matrix,
                **new_matrix,
                "rows": merge_transfer_rows(
                    new_matrix.get("rows", []),
                    prev_matrix.get("rows", []),
                ),
            }
            if new_matrix.get("rows"):
                matrix["last_updated"] = (
                    new_matrix.get("last_updated")
                    or merged.get("last_updated")
                    or utc_now_iso()
                )
            elif not matrix.get("last_updated"):
                matrix["last_updated"] = (
                    prev_matrix.get("last_updated")
                    or merged.get("last_updated")
                    or utc_now_iso()
                )
            merged["aud_npr_transfer_methods"] = matrix

    merged["fetch_mode"] = "snapshot"
    merged["cached"] = True
    merged["snapshot_refresh_seconds"] = refresh_seconds
    merged.pop("payload", None)
    return merged
