"""Tests for utility helpers."""

import pytest

from utils import compute_receive_amount, parse_rate_from_text, retry


def test_compute_receive_amount():
    net, receive = compute_receive_amount(1000.0, 6.5, 87.92)
    assert net == 993.5
    assert receive == round(993.5 * 87.92, 2)


def test_parse_rate_from_text():
    assert parse_rate_from_text("1 AUD = 87.92 NPR") == 87.92
    assert parse_rate_from_text("Exchange rate: 140.55 NPR") == 140.55
    assert parse_rate_from_text("no rate here") is None


def test_retry_succeeds_after_failure():
    attempts = {"count": 0}

    @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ValueError("temporary")
        return "ok"

    assert flaky() == "ok"
    assert attempts["count"] == 2


def test_retry_raises_after_max_attempts():
    @retry(max_attempts=2, delay=0.01, exceptions=(RuntimeError,))
    def always_fail():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        always_fail()
