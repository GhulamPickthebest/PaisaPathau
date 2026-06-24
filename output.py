"""JSON and CSV output generation for GitHub Pages and WordPress."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR
from constants import (
    ACTIVE_SEND_CURRENCIES,
    PROVIDER_PRIORITY,
    TIER_B_CORRIDORS,
    TIER_C_CURRENCIES,
)
from models import PipelineResult, RateRecord, utc_now_iso
from transfer_methods.aud_npr import fetch_aud_npr_transfer_methods
from utils import logger

CSV_FIELDS = [
    "provider",
    "customer_type",
    "rate_label",
    "from_currency",
    "from_country",
    "from_flag",
    "to_currency",
    "send_amount",
    "exchange_rate",
    "fee",
    "net_send_amount",
    "receive_amount",
    "transfer_speed",
    "delivery_method",
    "timestamp",
    "source",
    "status",
]


def build_output_payload(
    result: PipelineResult,
    send_amount: float,
    transfer_method_matrix: dict | None = None,
) -> dict:
    payload = {
        "last_updated": utc_now_iso(),
        "send_amount": send_amount,
        "total_corridors": len(result.unique_corridors),
        "total_providers": len(result.unique_providers),
        "corridors": result.corridors,
        "all_rates": [r.to_dict() for r in result.all_rates],
        "coverage": {
            "send_currencies": list(ACTIVE_SEND_CURRENCIES),
            "tier_b_providers": dict(TIER_B_CORRIDORS),
            "tier_c_currencies": list(TIER_C_CURRENCIES),
            "provider_priority": dict(PROVIDER_PRIORITY),
        },
    }
    if transfer_method_matrix:
        payload["aud_npr_transfer_methods"] = transfer_method_matrix
    return payload


def write_latest_json(payload: dict, data_dir: Path = DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "latest_rates.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    logger.info("Wrote %s", path)
    return path


def write_snapshot_json(payload: dict, data_dir: Path = DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    path = data_dir / f"rates_{stamp}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    logger.info("Wrote snapshot %s", path)
    return path


def write_csv(records: list[RateRecord], data_dir: Path = DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "latest_rates.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            row = record.to_dict()
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})
    logger.info("Wrote %s", path)
    return path


def write_aud_npr_transfer_methods(
    matrix: dict, data_dir: Path = DATA_DIR
) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "aud_npr_transfer_methods.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(matrix, fh, indent=2, ensure_ascii=False)
    logger.info("Wrote %s", path)
    return path


def write_all_outputs_from_payload(
    result: PipelineResult,
    payload: dict,
    send_amount: float,
) -> dict[str, Path]:
    transfer_matrix = payload.get("aud_npr_transfer_methods") or {}
    return {
        "latest_json": write_latest_json(payload),
        "snapshot_json": write_snapshot_json(payload),
        "csv": write_csv(result.all_rates),
        "aud_npr_methods": write_aud_npr_transfer_methods(transfer_matrix),
    }


def write_all_outputs(
    result: PipelineResult,
    send_amount: float,
    skip_browser: bool = False,
) -> dict[str, Path]:
    transfer_matrix = fetch_aud_npr_transfer_methods(
        send_amount=send_amount,
        skip_browser=skip_browser,
    )
    payload = build_output_payload(result, send_amount, transfer_matrix)
    return write_all_outputs_from_payload(result, payload, send_amount)
