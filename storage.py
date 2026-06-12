"""SQLite persistence for historical rate data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config import DATA_DIR
from models import RateRecord
from utils import logger

DB_PATH = DATA_DIR / "rates_history.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT,
    from_currency TEXT,
    exchange_rate REAL,
    fee REAL,
    receive_amount REAL,
    send_amount REAL,
    timestamp TEXT,
    status TEXT
);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(SCHEMA)
        conn.commit()
    logger.debug("Database initialized at %s", db_path)


def insert_rates(records: list[RateRecord], db_path: Path = DB_PATH) -> int:
    init_db(db_path)
    rows = [
        (
            r.provider,
            r.from_currency,
            r.exchange_rate,
            r.fee,
            r.receive_amount,
            r.send_amount,
            r.timestamp,
            r.status,
        )
        for r in records
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO rates (
                provider, from_currency, exchange_rate, fee,
                receive_amount, send_amount, timestamp, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    logger.info("Inserted %s records into %s", len(rows), db_path)
    return len(rows)


def get_recent_rates(limit: int = 100, db_path: Path = DB_PATH) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM rates ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
