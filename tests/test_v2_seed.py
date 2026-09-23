"""Tests for the deterministic demo scenario seed (SIH Prototype V2, Task M2)."""

from __future__ import annotations

import itertools
import math
from datetime import UTC, datetime
from pathlib import Path

from oilspill.demo_data.scenario import ORIGIN, SCENARIO, VESSELS
from oilspill.demo_data.seed import seed
from oilspill.store.db import get_conn, init_db


def _parse_z(value: str) -> datetime:
    assert value.endswith("Z"), f"timestamp must be ISO Z: {value!r}"
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _seeded_conn(tmp_path: Path):
    db_path = tmp_path / "demo.db"
    conn = get_conn(db_path)
    init_db(conn)
    return conn


def test_seed_counts(tmp_path: Path) -> None:
    """seed inserts 4 vessels and all fixed tracks; DB counts match."""
    conn = _seeded_conn(tmp_path)
    try:
        result = seed(conn)
        expected_tracks = sum(len(v["TRACKS"]) for v in VESSELS)
        assert result == {"vessels": 4, "tracks": expected_tracks}
        n_vessels = conn.execute("SELECT COUNT(*) AS n FROM vessels").fetchone()["n"]
        n_tracks = conn.execute("SELECT COUNT(*) AS n FROM vessel_tracks").fetchone()["n"]
        assert n_vessels == 4
        assert n_tracks == expected_tracks
    finally:
        conn.close()


def test_seed_deterministic(tmp_path: Path) -> None:
    """Seeding twice is idempotent; CORALIS stays dark with a >=2h AIS gap."""
    conn = _seeded_conn(tmp_path)
    try:
        first = seed(conn)
        second = seed(conn)
        assert first == second

        row = conn.execute(
            "SELECT dark_vessel FROM vessels WHERE id = ?", ("vessel-coralis",)
        ).fetchone()
        assert row is not None
        assert row["dark_vessel"] == 1

        tracks = conn.execute(
            "SELECT timestamp FROM vessel_tracks WHERE vessel_id = ? ORDER BY timestamp",
            ("vessel-coralis",),
        ).fetchall()
        assert len(tracks) >= 2
        times = [_parse_z(r["timestamp"]) for r in tracks]
        gaps = [(b - a).total_seconds() / 3600.0 for a, b in itertools.pairwise(times)]
        assert max(gaps) >= 2.0

        # All demo coords stay within 50km of the slick origin.
        for vessel in VESSELS:
            assert _haversine_km(ORIGIN["lat"], ORIGIN["lon"], vessel["lat"], vessel["lon"]) < 50.0
            for _ts, lat, lon, _speed, _heading in vessel["TRACKS"]:
                assert _haversine_km(ORIGIN["lat"], ORIGIN["lon"], lat, lon) < 50.0
    finally:
        conn.close()


def test_origin_matches_hindcast_defaults() -> None:
    """ORIGIN matches the documented hindcast slick defaults."""
    from oilspill.hindcast.models import CurrentOilSlick

    assert ORIGIN == {
        "lat": -20.44,
        "lon": 57.72,
        "detection_time": "2020-07-25T04:35:00Z",
        "slick_area_km2": 3.1,
    }
    slick = CurrentOilSlick(
        latitude=ORIGIN["lat"],
        longitude=ORIGIN["lon"],
        detection_time=_parse_z(ORIGIN["detection_time"]),
        slick_area_km2=ORIGIN["slick_area_km2"],
    )
    assert slick.latitude == -20.44
    assert slick.longitude == 57.72
    assert slick.slick_area_km2 == 3.1
    assert SCENARIO["origin"] == ORIGIN
