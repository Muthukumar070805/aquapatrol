"""On-screen incident report endpoint (SIH Prototype V2, Task M6)."""

from __future__ import annotations

import sqlite3
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from oilspill.api.correlations import DEMO_DETECTION_TIME
from oilspill.api.models import (
    REPORT_DISCLAIMER,
    InvestigationSignal,
    ReportResponse,
    Vessel,
)
from oilspill.api.settings import Settings
from oilspill.store.db import get_conn, init_db

router = APIRouter(tags=["reports"])


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


def _signal_level(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def _row_to_vessel(vrow: sqlite3.Row) -> Vessel:
    return Vessel(
        id=vrow["id"],
        name=vrow["name"],
        mmsi=vrow["mmsi"],
        imo=vrow["imo"],
        flag=vrow["flag"],
        vessel_type=vrow["vessel_type"],
        lat=vrow["lat"],
        lon=vrow["lon"],
        speed=vrow["speed"],
        heading=vrow["heading"],
        ais_status=vrow["ais_status"],
        dark_vessel=bool(vrow["dark_vessel"]),
        last_seen=vrow["last_seen"],
        source="simulated_ais",
    )


def _best_correlation(
    conn: sqlite3.Connection, case_id: str, vessel_id: str | None
) -> dict[str, Any] | None:
    # Scoped to this case only: never inherit adhoc or other cases' rows
    # via vessel_id fallback.
    row = conn.execute(
        "SELECT * FROM spill_vessel_correlations WHERE case_id = ? "
        "ORDER BY correlation_score DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    return dict(row) if row is not None else None


@router.get("/reports/{case_id}", response_model=ReportResponse)
def get_report(case_id: str, cfg: SettingsDep) -> ReportResponse:
    """Return a regenerable on-screen incident report for one case."""
    conn = _conn(cfg)
    try:
        row = conn.execute("SELECT * FROM investigation_cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

        vessel: Vessel | None = None
        selected_vessel_id = row["selected_vessel_id"]
        if selected_vessel_id is not None:
            vrow = conn.execute(
                "SELECT * FROM vessels WHERE id = ?",
                (selected_vessel_id,),
            ).fetchone()
            if vrow is not None:
                vessel = _row_to_vessel(vrow)

        correlation = _best_correlation(conn, case_id, selected_vessel_id)
        ev_rows = conn.execute(
            "SELECT * FROM case_evidence WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
        evidence: list[Any] = [dict(r) for r in ev_rows]

        if correlation is not None and correlation.get("correlation_score") is not None:
            score = float(correlation["correlation_score"])
        else:
            score = float(row["candidate_confidence"]) * 100.0
        signal = InvestigationSignal(
            level=_signal_level(score),
            score=score,
            status="REQUIRES INVESTIGATION",
        )

        return ReportResponse(
            case_id=row["id"],
            case_number=row["case_number"],
            observation_time=DEMO_DETECTION_TIME,
            spill_candidate={
                "spill_id": row["spill_id"],
                "confidence": row["candidate_confidence"],
            },
            estimated_origin={
                "lat": row["origin_lat"],
                "lon": row["origin_lon"],
                "confidence": row["origin_confidence"],
            },
            vessel=vessel,
            correlation=correlation,
            evidence=evidence,
            investigation_signal=signal,
            disclaimer=REPORT_DISCLAIMER,
        )
    finally:
        conn.close()


__all__ = ["router"]
