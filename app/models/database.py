"""SQLite database initialization and query helpers."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


def init_db(db_path: str) -> None:
    """Create database directory and tables if they do not exist."""
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL NOT NULL,
                ram_percent REAL NOT NULL,
                disk_percent REAL NOT NULL,
                net_bytes_sent INTEGER NOT NULL,
                net_bytes_recv INTEGER NOT NULL,
                response_time_ms REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                source TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                threshold REAL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                acknowledged INTEGER NOT NULL DEFAULT 0,
                acknowledged_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                message TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection(db_path: str):
    """Yield a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def insert_metric_snapshot(db_path: str, snapshot: dict) -> None:
    """Persist a single metrics snapshot and prune records older than 2000 rows."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO metrics_history (
                timestamp, cpu_percent, ram_percent, disk_percent,
                net_bytes_sent, net_bytes_recv, response_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["timestamp"],
                snapshot["cpu_percent"],
                snapshot["ram_percent"],
                snapshot["disk_percent"],
                snapshot["net_bytes_sent"],
                snapshot["net_bytes_recv"],
                snapshot.get("response_time_ms", 0.0),
            ),
        )
        conn.execute(
            """
            DELETE FROM metrics_history
            WHERE id NOT IN (
                SELECT id FROM metrics_history ORDER BY id DESC LIMIT 2000
            )
            """
        )
        conn.commit()


def fetch_metrics_history(db_path: str, limit: int = 60) -> list[dict]:
    """Return recent metrics history ordered chronologically."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT timestamp, cpu_percent, ram_percent, disk_percent,
                   net_bytes_sent, net_bytes_recv, response_time_ms
            FROM metrics_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def insert_log(db_path: str, level: str, source: str, message: str) -> None:
    """Store a structured application log event in SQLite."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO app_logs (timestamp, level, source, message)
            VALUES (?, ?, ?, ?)
            """,
            (utc_now_iso(), level.upper(), source, message),
        )
        conn.execute(
            """
            DELETE FROM app_logs
            WHERE id NOT IN (
                SELECT id FROM app_logs ORDER BY id DESC LIMIT 500
            )
            """
        )
        conn.commit()


def fetch_logs(db_path: str, level: str | None = None, limit: int = 100) -> list[dict]:
    """Retrieve recent application logs, optionally filtered by level."""
    with get_connection(db_path) as conn:
        if level and level.upper() != "ALL":
            rows = conn.execute(
                """
                SELECT id, timestamp, level, source, message
                FROM app_logs
                WHERE level = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (level.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, timestamp, level, source, message
                FROM app_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]
