"""Merge new fetch results with the last successful snapshot."""

from __future__ import annotations

from typing import Any

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


def merge_rate_records(
    new_records: list[dict[str, Any]],
    previous_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep last successful quote when a provider fails on the next run."""
    previous_ok = {
        rate_record_key(record): record
        for record in previous_records
        if record.get("status") == "ok"
    }
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for record in new_records:
        key = rate_record_key(record)
        seen.add(key)
        if record.get("status") == "ok":
            merged.append(record)
            continue
        if key in previous_ok:
            merged.append(dict(previous_ok[key]))
            continue
        merged.append(record)

    for key, record in previous_ok.items():
        if key not in seen:
            merged.append(record)

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
            merged.append(row)
            continue
        if key in previous_ok:
            merged.append(dict(previous_ok[key]))
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
    else:
        merged = dict(new_payload)
        merged["all_rates"] = merge_rate_records(
            new_payload.get("all_rates", []),
            previous_payload.get("all_rates", []),
        )
        new_matrix = new_payload.get("aud_npr_transfer_methods") or {}
        prev_matrix = previous_payload.get("aud_npr_transfer_methods") or {}
        if new_matrix or prev_matrix:
            merged["aud_npr_transfer_methods"] = {
                **new_matrix,
                **{k: v for k, v in prev_matrix.items() if k != "rows"},
                "rows": merge_transfer_rows(
                    new_matrix.get("rows", []),
                    prev_matrix.get("rows", []),
                ),
            }

    merged["fetch_mode"] = "snapshot"
    merged["cached"] = True
    merged["snapshot_refresh_seconds"] = refresh_seconds
    merged.pop("payload", None)
    return merged
