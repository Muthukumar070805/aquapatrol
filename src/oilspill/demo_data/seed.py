"""Idempotent seed of the deterministic demo scenario (source: simulated_ais)."""

from __future__ import annotations

import sqlite3

from oilspill.demo_data.scenario import VESSELS
from oilspill.store.db import init_db

_VESSEL_COLUMNS = (
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
)


def seed(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert demo vessels and tracks; safe to call repeatedly.

    Vessels use ``INSERT OR REPLACE`` on their text primary key. Tracks have
    an autoincrement key with no natural unique constraint, so existing demo
    tracks are deleted before re-inserting the fixed points — the visible
    result is idempotent. Returns ``{"vessels": 4, "tracks": N}``.
    """
    init_db(conn)
    for vessel in VESSELS:
        conn.execute(
            "INSERT OR REPLACE INTO vessels "
            "(id, name, mmsi, imo, flag, vessel_type, lat, lon, speed, "
            "heading, ais_status, dark_vessel, last_seen) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(vessel[col] for col in _VESSEL_COLUMNS),
        )
    vessel_ids = [vessel["id"] for vessel in VESSELS]
    placeholders = ",".join("?" for _ in vessel_ids)
    conn.execute(f"DELETE FROM vessel_tracks WHERE vessel_id IN ({placeholders})", vessel_ids)
    track_count = 0
    for vessel in VESSELS:
        for timestamp, lat, lon, speed, heading in vessel["TRACKS"]:
            conn.execute(
                "INSERT OR REPLACE INTO vessel_tracks "
                "(vessel_id, timestamp, lat, lon, speed, heading) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (vessel["id"], timestamp, lat, lon, speed, heading),
            )
            track_count += 1
    conn.commit()
    return {"vessels": len(VESSELS), "tracks": track_count}


__all__ = ["seed"]
