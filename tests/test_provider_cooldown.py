"""Tests for provider rate-limit cooldown."""

from provider_cooldown import (
    clear_cooldown,
    is_cooling_down,
    mark_rate_limited,
    remaining_seconds,
)


def test_mark_rate_limited_sets_cooldown():
    clear_cooldown("Remitly")
    assert is_cooling_down("Remitly") is False
    mark_rate_limited("Remitly", seconds=60)
    assert is_cooling_down("Remitly") is True
    assert remaining_seconds("Remitly") > 0
    clear_cooldown("Remitly")
    assert is_cooling_down("Remitly") is False
