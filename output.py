"""JSON and CSV output generation for GitHub Pages and WordPress."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR
from models import PipelineResult, RateRecord, utc_now_iso
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


def build_output_payload(result: PipelineResult, send_amount: float) -> dict:
    return {
        "last_updated": utc_now_iso(),
        "send_amount": send_amount,
        "total_corridors": len(result.unique_corridors),
        "total_providers": len(result.unique_providers),
        "corridors": result.corridors,
        "all_rates": [r.to_dict() for r in result.all_rates],
    }


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


def write_all_outputs(result: PipelineResult, send_amount: float) -> dict[str, Path]:
    payload = build_output_payload(result, send_amount)
    return {
        "latest_json": write_latest_json(payload),
        "snapshot_json": write_snapshot_json(payload),
        "csv": write_csv(result.all_rates),
    }
