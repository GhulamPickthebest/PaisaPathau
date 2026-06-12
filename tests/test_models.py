"""Tests for RateRecord and PipelineResult models."""

from models import PipelineResult, RateRecord


def test_rate_record_computes_net_send():
    record = RateRecord(
        provider="Wise",
        from_currency="AUD",
        to_currency="NPR",
        exchange_rate=88.0,
        send_amount=1000.0,
        receive_amount=87120.0,
        fee=10.0,
        timestamp="2026-06-11T12:00:00+00:00",
        status="ok",
    )
    assert record.net_send_amount == 990.0
    assert record.from_country == "Australia"
    assert record.from_flag == "🇦🇺"


def test_error_record():
    record = RateRecord.error_record("Remitly", "USD", 1000.0, source="scraper")
    assert record.status == "error"
    assert record.exchange_rate == 0.0
    assert record.source == "scraper"


def test_pipeline_result_corridors():
    rates = [
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
        ),
        RateRecord(
            provider="Remitly",
            from_currency="AUD",
            to_currency="NPR",
            exchange_rate=87.0,
            send_amount=1000.0,
            receive_amount=87000.0,
            fee=0.0,
            timestamp="2026-06-11T12:00:00+00:00",
            status="ok",
        ),
    ]
    result = PipelineResult(all_rates=rates)
    corridors = result.corridors
    assert len(corridors) == 1
    assert corridors[0]["from_currency"] == "AUD"
    assert len(corridors[0]["rates"]) == 2
