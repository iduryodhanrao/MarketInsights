"""
Database Module
───────────────
SQLite persistence layer for watchlist symbols and cached market
insights.  Tables are auto-created on first import.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_insights.db")


# ── Connection helper ────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    """Return a new SQLite connection with row-factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ── Schema bootstrap ────────────────────────────────────────────

def init_db():
    """Create tables if they do not already exist."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL UNIQUE,
            added_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS insights_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            payload     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS watchlist_recommendations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            signal      TEXT    NOT NULL,
            confidence  TEXT    NOT NULL DEFAULT 'MEDIUM',
            reasoning   TEXT    NOT NULL DEFAULT '',
            sources     TEXT    NOT NULL DEFAULT '[]',
            price       REAL    NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ── Watchlist CRUD ───────────────────────────────────────────────

def get_watchlist() -> list[dict]:
    """Return all symbols currently on the watchlist."""
    conn = _connect()
    rows = conn.execute("SELECT symbol, added_at FROM watchlist ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_to_watchlist(symbol: str) -> dict:
    """Add a ticker symbol to the watchlist (uppercased, deduplicated)."""
    symbol = symbol.strip().upper()
    conn = _connect()
    try:
        conn.execute("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (symbol,))
        conn.commit()
    finally:
        conn.close()
    return {"symbol": symbol, "status": "added"}


def remove_from_watchlist(symbol: str) -> dict:
    """Remove a ticker symbol from the watchlist."""
    symbol = symbol.strip().upper()
    conn = _connect()
    conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()
    return {"symbol": symbol, "status": "removed"}


# ── Insights cache ───────────────────────────────────────────────

def save_insights(payload: dict):
    """Persist the latest insights payload to the cache table."""
    conn = _connect()
    conn.execute("INSERT INTO insights_cache (payload) VALUES (?)", (json.dumps(payload),))
    conn.commit()
    conn.close()


def get_cached_insights() -> dict | None:
    """Return the most recent cached insights, or None if empty."""
    conn = _connect()
    row = conn.execute(
        "SELECT payload, created_at FROM insights_cache ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        data = json.loads(row["payload"])
        data["_cached_at"] = row["created_at"]
        return data
    return None


# ── Watchlist recommendations ────────────────────────────────────

def save_recommendations(recs: list[dict]):
    """Persist a batch of buy/sell recommendations for watchlist symbols."""
    conn = _connect()
    conn.execute("DELETE FROM watchlist_recommendations")
    for r in recs:
        conn.execute(
            "INSERT INTO watchlist_recommendations (symbol, signal, confidence, reasoning, sources, price) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                r.get("symbol", ""),
                r.get("signal", "HOLD"),
                r.get("confidence", "MEDIUM"),
                r.get("reasoning", ""),
                json.dumps(r.get("sources", [])),
                r.get("price", 0),
            ),
        )
    conn.commit()
    conn.close()


def get_recommendations() -> list[dict]:
    """Return the latest recommendations for all watchlist symbols."""
    conn = _connect()
    rows = conn.execute(
        "SELECT symbol, signal, confidence, reasoning, sources, price, created_at "
        "FROM watchlist_recommendations ORDER BY id"
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["sources"] = json.loads(d["sources"])
        results.append(d)
    return results


# ── Auto-initialise on import ────────────────────────────────────
init_db()
