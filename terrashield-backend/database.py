"""
SQLite database initialisation and thread-safe connection management.

Uses WAL journal mode so the simulator threads (writers) and Flask
request threads (readers) never block each other.
"""

import sqlite3
import threading
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terrashield.db")

# Thread-local storage so each thread gets its own connection
_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Return (and lazily create) a per-thread SQLite connection."""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db() -> None:
    """Create all tables and indexes on first run (idempotent)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        -- Every sensor reading (real + ghost)
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id      TEXT    NOT NULL,
            domain         TEXT    NOT NULL,          -- water | soil | health
            timestamp      TEXT    NOT NULL,          -- ISO-8601 UTC
            values_json    TEXT    NOT NULL,          -- JSON payload
            hmac_signature TEXT    NOT NULL,          -- HMAC-SHA256 hex
            region         TEXT    NOT NULL DEFAULT 'REGION-1',
            is_ghost       INTEGER NOT NULL DEFAULT 0  -- 1 = ghost / honeypot reading
        );

        -- Intrusion events caught by ghost sensors
        CREATE TABLE IF NOT EXISTS ghost_intrusions (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            ghost_id             TEXT NOT NULL,
            timestamp            TEXT NOT NULL,
            attacker_ip          TEXT,
            attacker_fingerprint TEXT NOT NULL,   -- SHA-256 of payload+timestamp
            payload              TEXT NOT NULL
        );

        -- Anomaly events emitted by the correlation engine
        CREATE TABLE IF NOT EXISTS anomaly_events (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp               TEXT NOT NULL,
            confidence              REAL NOT NULL,
            flagged_domains         TEXT NOT NULL,          -- comma-separated
            correlation_scores_json TEXT NOT NULL,
            rules_violated          TEXT NOT NULL           -- semicolon-separated
        );

        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_readings_domain    ON sensor_readings(domain);
        CREATE INDEX IF NOT EXISTS idx_readings_ts        ON sensor_readings(timestamp);
        CREATE INDEX IF NOT EXISTS idx_readings_sensor    ON sensor_readings(sensor_id);
        CREATE INDEX IF NOT EXISTS idx_ghost_ts           ON ghost_intrusions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_anomaly_ts         ON anomaly_events(timestamp);
        """
    )
    conn.commit()
    conn.close()
    print(f"[DB] Initialised → {DB_PATH}")
