"""Tests for SQLite storage layer."""

import sqlite3
from pathlib import Path

from models import RateRecord
from storage import get_recent_rates, init_db, insert_rates


def test_init_db_creates_table(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rates'"
        )
        assert cursor.fetchone() is not None


def test_insert_and_query_rates(tmp_path: Path):
    db_path = tmp_path / "test.db"
    record = RateRecord(
        provider="Wise",
        from_currency="AUD",
        to_currency="NPR",
        exchange_rate=88.5,
        send_amount=1000.0,
        receive_amount=88500.0,
        fee=0.0,
        timestamp="2026-06-11T12:00:00+00:00",
        status="ok",
    )
    count = insert_rates([record], db_path=db_path)
    assert count == 1

    rows = get_recent_rates(limit=10, db_path=db_path)
    assert len(rows) == 1
    assert rows[0]["provider"] == "Wise"
    assert rows[0]["exchange_rate"] == 88.5
