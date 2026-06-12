"""Tests for JSON/CSV output generation."""

import json
from pathlib import Path

from models import PipelineResult, RateRecord
from output import build_output_payload, write_all_outputs


def _sample_result() -> PipelineResult:
    return PipelineResult(
        all_rates=[
            RateRecord(
                provider="Wise",
                from_currency="AUD",
                to_currency="NPR",
                exchange_rate=88.0,
                send_amount=1000.0,
                receive_amount=88000.0,
                fee=0.0,
                timestamp="2026-06-11T12:00:00+00:00",
                status="ok",
            )
        ]
    )


def test_build_output_payload():
    payload = build_output_payload(_sample_result(), send_amount=1000.0)
    assert payload["send_amount"] == 1000.0
    assert payload["total_providers"] == 1
    assert len(payload["all_rates"]) == 1
    assert "last_updated" in payload


def test_write_all_outputs(tmp_path: Path, monkeypatch):
    import output as output_module

    monkeypatch.setattr(output_module, "DATA_DIR", tmp_path)
    paths = write_all_outputs(_sample_result(), send_amount=1000.0)

    assert paths["latest_json"].exists()
    assert paths["csv"].exists()
    assert paths["snapshot_json"].exists()

    with paths["latest_json"].open() as fh:
        data = json.load(fh)
    assert data["all_rates"][0]["provider"] == "Wise"
