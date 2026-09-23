"""Vessel intelligence endpoints (simulated AIS, seed-on-empty)."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from oilspill.api.models import Vessel, VesselListResponse, VesselTrackPoint
from oilspill.api.settings import Settings
from oilspill.store.db import get_conn, init_db

router = APIRouter(tags=["vessels"])


def _get_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


SettingsDep = Annotated[Settings, Depends(_get_settings)]


def _conn(settings: Settings) -> sqlite3.Connection:
    """Open the prototype DB, init schema, seed demo vessels if empty."""
    from oilspill.demo_data.seed import seed

    conn = get_conn(settings.prototype_db)
    try:
        init_db(conn)
        row = conn.execute("SELECT COUNT(*) AS n FROM vessels").fetchone()
        if row is not None and int(row["n"]) == 0:
            seed(conn)
    except Exception:
        conn.close()
        raise
    return conn


def _row_to_vessel(row: sqlite3.Row) -> Vessel:
    return Vessel(
        id=row["id"],
        name=row["name"],
        mmsi=row["mmsi"],
        imo=row["imo"],
        flag=row["flag"],
        vessel_type=row["vessel_type"],
        lat=row["lat"],
        lon=row["lon"],
        speed=row["speed"],
        heading=row["heading"],
        ais_status=row["ais_status"],
        dark_vessel=bool(row["dark_vessel"]),
        last_seen=row["last_seen"],
        source="simulated_ais",
    )


@router.get("/vessels", response_model=VesselListResponse)
def list_vessels(cfg: SettingsDep) -> VesselListResponse:
    """Return all vessels, seeding the demo scenario when the table is empty."""
    conn = _conn(cfg)
    try:
        rows = conn.execute("SELECT * FROM vessels ORDER BY id").fetchall()
        vessels = [_row_to_vessel(row) for row in rows]
    finally:
        conn.close()
    return VesselListResponse(vessels=vessels, source="simulated_ais")


@router.get("/vessels/{vessel_id}", response_model=Vessel)
def get_vessel(vessel_id: str, cfg: SettingsDep) -> Vessel:
    """Return one vessel by id, or 404 when unknown."""
    conn = _conn(cfg)
    try:
        row = conn.execute("SELECT * FROM vessels WHERE id = ?", (vessel_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Vessel not found: {vessel_id}")
        return _row_to_vessel(row)
    finally:
        conn.close()


@router.get("/vessels/{vessel_id}/track", response_model=list[VesselTrackPoint])
def get_vessel_track(vessel_id: str, cfg: SettingsDep) -> list[VesselTrackPoint]:
    """Return a vessel's track points ordered by timestamp."""
    conn = _conn(cfg)
    try:
        vessel = conn.execute("SELECT id FROM vessels WHERE id = ?", (vessel_id,)).fetchone()
        if vessel is None:
            raise HTTPException(status_code=404, detail=f"Vessel not found: {vessel_id}")
        rows = conn.execute(
            "SELECT timestamp, lat, lon, speed, heading FROM vessel_tracks "
            "WHERE vessel_id = ? ORDER BY timestamp",
            (vessel_id,),
        ).fetchall()
        return [
            VesselTrackPoint(
                timestamp=row["timestamp"],
                lat=row["lat"],
                lon=row["lon"],
                speed=row["speed"],
                heading=row["heading"],
            )
            for row in rows
        ]
    finally:
        conn.close()


__all__ = ["router"]
