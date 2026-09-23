"""Investigative spill-vessel correlation endpoint (heuristic_v1)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from oilspill.api.models import CORRELATION_DISCLAIMER, CorrelationRequest, CorrelationResponse
from oilspill.api.settings import Settings
from oilspill.forensics.correlation import haversine_km, score_correlation
from oilspill.store.db import get_conn, init_db

router = APIRouter(tags=["correlations"])

_DETECTION_TIME = datetime(2020, 7, 25, 4, 35, 0, tzinfo=UTC)
DEMO_DETECTION_TIME = "2020-07-25T04:35:00Z"


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


def _parse_z(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


@router.post("/correlations", response_model=CorrelationResponse)
def create_correlation(body: CorrelationRequest, cfg: SettingsDep) -> CorrelationResponse:
    """Score one candidate vessel against a slick origin (investigative)."""
    conn = _conn(cfg)
    try:
        row = conn.execute("SELECT * FROM vessels WHERE id = ?", (body.vessel_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Vessel not found: {body.vessel_id}")
        vessel_lat = float(row["lat"])
        vessel_lon = float(row["lon"])
        last_seen = _parse_z(str(row["last_seen"]))
        dark = bool(row["dark_vessel"])

        detection_time = _DETECTION_TIME
        if body.detection_time is not None:
            try:
                detection_time = _parse_z(body.detection_time)
            except ValueError as exc:
                raise HTTPException(
                    status_code=422, detail=f"Invalid detection_time: {body.detection_time}"
                ) from exc

        case_id = body.case_id or "adhoc"
        if case_id != "adhoc":
            case_row = conn.execute(
                "SELECT id FROM investigation_cases WHERE id = ?", (case_id,)
            ).fetchone()
            if case_row is None:
                raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

        distance = haversine_km(body.origin_lat, body.origin_lon, vessel_lat, vessel_lon)
        time_diff_h = abs((detection_time - last_seen).total_seconds() / 3600.0)
        scored = score_correlation(
            distance, time_diff_h, body.trajectory_match, body.ais_visibility
        )
        conn.execute(
            "INSERT OR IGNORE INTO investigation_cases (id, case_number) VALUES (?, ?)",
            ("adhoc", "adhoc"),
        )
        conn.execute(
            "INSERT INTO spill_vessel_correlations "
            "(case_id, vessel_id, distance_km, time_difference_hours, "
            "trajectory_match, dark_vessel_indicator, correlation_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                case_id,
                body.vessel_id,
                float(scored["distance_km"]),
                float(scored["time_difference_hours"]),
                str(scored["trajectory_match"]),
                int(dark),
                float(scored["correlation_score"]),
            ),
        )
        conn.commit()
        return CorrelationResponse(
            vessel_id=body.vessel_id,
            distance_km=float(scored["distance_km"]),
            time_difference_hours=float(scored["time_difference_hours"]),
            trajectory_match=scored["trajectory_match"],
            ais_visibility=scored["ais_visibility"],
            dark_vessel_indicator=dark,
            correlation_score=float(scored["correlation_score"]),
            method="heuristic_v1",
            disclaimer=CORRELATION_DISCLAIMER,
        )
    finally:
        conn.close()


__all__ = ["router"]
