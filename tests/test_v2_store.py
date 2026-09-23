"""Tests for the sqlite prototype store (SIH Prototype V2, Task M1)."""

import sqlite3
from pathlib import Path

from oilspill.store.db import get_conn, init_db

EXPECTED_TABLES = {
    "investigation_cases",
    "vessels",
    "vessel_tracks",
    "spill_vessel_correlations",
    "case_evidence",
}

# SQLite internal bookkeeping tables that may appear alongside user tables.
ALLOWED_INTERNAL_TABLES = {"sqlite_sequence", "sqlite_stat1"}

EXPECTED_VESSELS_COLUMNS = [
    "id",
    "name",
    "mmsi",
    "imo",
    "flag",
    "vessel_type",
    "lat",
    "lon",
    "speed",
    "heading",
    "ais_status",
    "dark_vessel",
    "last_seen",
]

EXPECTED_CASES_COLUMNS = [
    "id",
    "case_number",
    "created_at",
    "status",
    "spill_id",
    "candidate_confidence",
    "origin_lat",
    "origin_lon",
    "origin_confidence",
    "risk_level",
    "selected_vessel_id",
    "summary",
]


def _table_names(db_path: Path) -> set[str]:
    conn = get_conn(db_path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {row["name"] for row in rows}
    finally:
        conn.close()


def _column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row["name"] for row in rows]


def test_init_creates_five_tables(tmp_path: Path) -> None:
    """init_db creates exactly the five prototype tables."""
    db_path = tmp_path / "prototype.db"
    conn = get_conn(db_path)
    try:
        init_db(conn)
    finally:
        conn.close()
    assert _table_names(db_path) - ALLOWED_INTERNAL_TABLES == EXPECTED_TABLES


def test_init_idempotent(tmp_path: Path) -> None:
    """Running init_db twice does not fail and keeps the five tables."""
    db_path = tmp_path / "prototype.db"
    conn = get_conn(db_path)
    try:
        init_db(conn)
        init_db(conn)
    finally:
        conn.close()
    assert _table_names(db_path) - ALLOWED_INTERNAL_TABLES == EXPECTED_TABLES


def test_expected_columns(tmp_path: Path) -> None:
    """vessels and investigation_cases expose the expected column lists."""
    db_path = tmp_path / "prototype.db"
    conn = get_conn(db_path)
    try:
        init_db(conn)
        assert _column_names(conn, "vessels") == EXPECTED_VESSELS_COLUMNS
        assert _column_names(conn, "investigation_cases") == EXPECTED_CASES_COLUMNS
    finally:
        conn.close()


def test_init_idempotent_with_data(tmp_path: Path) -> None:
    """Rows inserted before a second init_db survive the re-run."""
    db_path = tmp_path / "prototype.db"
    conn = get_conn(db_path)
    try:
        init_db(conn)
        conn.execute("INSERT INTO vessels (id, name) VALUES (?, ?)", ("v-1", "Test Ship"))
        conn.commit()
        init_db(conn)
        row = conn.execute("SELECT id, name FROM vessels WHERE id = ?", ("v-1",)).fetchone()
        assert row is not None
        assert row["id"] == "v-1"
        assert row["name"] == "Test Ship"
    finally:
        conn.close()


def test_get_conn_uses_row_factory(tmp_path: Path) -> None:
    """get_conn returns connections whose rows are sqlite3.Row objects."""
    db_path = tmp_path / "prototype.db"
    conn = get_conn(db_path)
    try:
        assert conn.row_factory is sqlite3.Row
        init_db(conn)
        conn.execute("INSERT INTO vessels (id, name) VALUES (?, ?)", ("v-2", "Row Ship"))
        row = conn.execute("SELECT id FROM vessels WHERE id = ?", ("v-2",)).fetchone()
        assert isinstance(row, sqlite3.Row)
    finally:
        conn.close()
