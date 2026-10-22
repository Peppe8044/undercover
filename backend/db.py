"""The UnderCover database: SQLite, seeded from data/."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_DB = Path(__file__).resolve().parent / "undercover.db"

SCHEMA = """
DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS policies;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS handlers;
DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS steps;
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    record TEXT NOT NULL,
    status TEXT NOT NULL,
    thread_id TEXT,
    decision TEXT,
    payout REAL,
    reason TEXT,
    policy_section TEXT,
    decided_at TEXT,
    paid_amount REAL,
    paid_at TEXT,
    signed_off_by TEXT,
    signed_off_at TEXT
);
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE handlers (handler_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE settings (name TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def path() -> Path:
    """Return the database file, from UNDERCOVER_DB or the default."""
    return Path(os.getenv("UNDERCOVER_DB", str(DEFAULT_DB)))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database for one unit of work, committed at the end."""
    connection = sqlite3.connect(path())
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def load(name: str) -> Any:
    """Read a JSON file from data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed() -> dict[str, int]:
    """Create the database afresh from data/ and return what it holds."""
    claims = load("claims.json")
    policies = load("policies.json")
    customers = load("customers.json")
    handlers = load("handlers.json")
    with connect() as db:
        db.executescript(SCHEMA)
        db.executemany(
            "INSERT INTO claims (claim_id, record, status) VALUES (?, ?, 'waiting')",
            [(claim["claim_id"], json.dumps(claim)) for claim in claims],
        )
        db.executemany(
            "INSERT INTO policies VALUES (?, ?)",
            [(policy["policy_id"], json.dumps(policy)) for policy in policies],
        )
        db.executemany(
            "INSERT INTO customers VALUES (?, ?)",
            [(customer["customer_id"], json.dumps(customer)) for customer in customers],
        )
        db.executemany(
            "INSERT INTO handlers VALUES (?, ?)",
            [(handler["handler_id"], json.dumps(handler)) for handler in handlers],
        )
        db.executemany(
            "INSERT INTO settings VALUES (?, ?)",
            [
                ("company", json.dumps(load("company.json"))),
                ("plans", json.dumps(load("plans.json"))),
            ],
        )
    return {
        "claims": len(claims),
        "policies": len(policies),
        "customers": len(customers),
        "handlers": len(handlers),
    }


def setting(db: sqlite3.Connection, name: str) -> Any:
    """Return one of the company's settings: company or plans."""
    row = db.execute("SELECT record FROM settings WHERE name = ?", (name,)).fetchone()
    return json.loads(row["record"])
