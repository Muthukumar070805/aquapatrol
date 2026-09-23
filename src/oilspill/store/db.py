"""SQLite connection and schema helpers for the prototype store."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS investigation_cases (
        id TEXT PRIMARY KEY,
        case_number TEXT UNIQUE,
        created_at TEXT,
        status TEXT,
        spill_id TEXT,
        candidate_confidence REAL,
        origin_lat REAL,
        origin_lon REAL,
        origin_confidence REAL,
        risk_level TEXT,
        selected_vessel_id TEXT,
        summary TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS vessels (
        id TEXT PRIMARY KEY,
        name TEXT,
        mmsi TEXT,
        imo TEXT,
        flag TEXT,
        vessel_type TEXT,
        lat REAL,
        lon REAL,
        speed REAL,
        heading REAL,
        ais_status TEXT,
        dark_vessel INTEGER,
        last_seen TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS vessel_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vessel_id TEXT REFERENCES vessels (id),
        timestamp TEXT,
        lat REAL,
        lon REAL,
        speed REAL,
        heading REAL,
        FOREIGN KEY (vessel_id) REFERENCES vessels (id)
    )""",
    """CREATE TABLE IF NOT EXISTS spill_vessel_correlations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT REFERENCES investigation_cases (id),
        vessel_id TEXT REFERENCES vessels (id),
        distance_km REAL,
        time_difference_hours REAL,
        trajectory_match TEXT,
        dark_vessel_indicator INTEGER,
        correlation_score REAL,
        FOREIGN KEY (case_id) REFERENCES investigation_cases (id),
        FOREIGN KEY (vessel_id) REFERENCES vessels (id)
    )""",
    """CREATE TABLE IF NOT EXISTS case_evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT REFERENCES investigation_cases (id),
        evidence_type TEXT,
        title TEXT,
        description TEXT,
        confidence REAL,
        source TEXT,
        FOREIGN KEY (case_id) REFERENCES investigation_cases (id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_vessel_tracks_vessel_id ON vessel_tracks (vessel_id)",
    "CREATE INDEX IF NOT EXISTS idx_correlations_case_id ON spill_vessel_correlations (case_id)",
    "CREATE INDEX IF NOT EXISTS idx_correlations_vessel_id "
    "ON spill_vessel_correlations (vessel_id)",
    "CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON case_evidence (case_id)",
)


def get_conn(db_path: str | os.PathLike[str] | Path) -> sqlite3.Connection:
    """Open a SQLite connection with ``Row`` row factory."""
    path = Path(db_path)
    parent = path.parent
    if str(parent) and parent != Path("."):
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the five prototype tables if they do not exist."""
    for statement in _SCHEMA_STATEMENTS:
        conn.execute(statement)
    conn.commit()


__all__ = ["get_conn", "init_db"]
