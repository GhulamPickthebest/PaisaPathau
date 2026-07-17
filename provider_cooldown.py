"""Per-provider cooldown after rate limits (e.g. Remitly 429)."""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_cooldown_until: dict[str, float] = {}


def is_cooling_down(provider: str) -> bool:
    with _lock:
        until = _cooldown_until.get(provider)
        if until is None:
            return False
        if time.monotonic() >= until:
            _cooldown_until.pop(provider, None)
            return False
        return True


def remaining_seconds(provider: str) -> int:
    with _lock:
        until = _cooldown_until.get(provider)
        if until is None:
            return 0
        return max(0, int(until - time.monotonic()))


def mark_rate_limited(provider: str, seconds: float = 300.0) -> None:
    with _lock:
        _cooldown_until[provider] = time.monotonic() + seconds


def clear_cooldown(provider: str) -> None:
    with _lock:
        _cooldown_until.pop(provider, None)
