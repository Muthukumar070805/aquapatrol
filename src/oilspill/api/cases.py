"""Investigation cases endpoints (SIH Prototype V2, Task M5)."""

from __future__ import annotations

import secrets
import sqlite3
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from oilspill.api.models import CaseCreate, CaseDetail, CaseResponse, Vessel
from oilspill.api.settings import Settings
from oilspill.store.db import get_conn, init_db

router = APIRouter(tags=["cases"])


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


def _now_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _risk_level(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def _case_score(candidate_confidence: float, max_corr: float | None) -> float:
    if max_corr is not None:
        return float(max_corr)
    return float(candidate_confidence) * 100.0


def _max_correlation(
    conn: sqlite3.Connection, case_id: str | None, vessel_id: str | None = None
) -> float | None:
    # Scoped to this case only. Vessel fallback is intentionally omitted:
    # inheriting adhoc (or other cases') scores via vessel_id leaks across cases.
    if case_id is not None:
        row = conn.execute(
            "SELECT MAX(correlation_score) AS m FROM spill_vessel_correlations WHERE case_id = ?",
            (case_id,),
        ).fetchone()
        if row is not None and row["m"] is not None:
            return float(row["m"])
        return None
    if vessel_id is None:
        return None
    row = conn.execute(
        "SELECT MAX(correlation_score) AS m FROM spill_vessel_correlations "
        "WHERE vessel_id = ? AND case_id != 'adhoc'",
        (vessel_id,),
    ).fetchone()
    if row is None or row["m"] is None:
        return None
    return float(row["m"])


def _timeline() -> list[str]:
    return [
        "Satellite observation received",
        "Oil candidate detected",
        "Probable Origin estimated",
        "Vessel correlation completed",
        "Evidence compiled",
        "Risk level assessed",
        "Investigation Case Created",
    ]


def _row_to_case_response(row: sqlite3.Row) -> CaseResponse:
    return CaseResponse(
        id=row["id"],
        case_number=row["case_number"],
        status=row["status"],
        spill_id=row["spill_id"],
        candidate_confidence=row["candidate_confidence"],
        origin_lat=row["origin_lat"],
        origin_lon=row["origin_lon"],
        origin_confidence=row["origin_confidence"],
        risk_level=row["risk_level"],
        selected_vessel_id=row["selected_vessel_id"],
        summary=row["summary"],
        created_at=row["created_at"],
    )


def _next_case_number(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM investigation_cases WHERE case_number LIKE 'SIH-%'"
    ).fetchone()
    n = int(row["n"]) if row is not None else 0
    candidate = f"SIH-2026-{n + 1:03d}"
    # Guard against manual inserts / adhoc collisions.
    while (
        conn.execute(
            "SELECT 1 FROM investigation_cases WHERE case_number = ?",
            (candidate,),
        ).fetchone()
        is not None
    ):
        n += 1
        candidate = f"SIH-2026-{n + 1:03d}"
    return candidate


@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(body: CaseCreate, cfg: SettingsDep) -> CaseResponse:
    """Open an investigation case with auto evidence + timeline."""
    conn = _conn(cfg)
    try:
        if body.selected_vessel_id is not None:
            vessel = conn.execute(
                "SELECT id FROM vessels WHERE id = ?",
                (body.selected_vessel_id,),
            ).fetchone()
            if vessel is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Vessel not found: {body.selected_vessel_id}",
                )
        case_id = secrets.token_hex(4)
        while (
            conn.execute("SELECT 1 FROM investigation_cases WHERE id = ?", (case_id,)).fetchone()
            is not None
        ):
            case_id = secrets.token_hex(4)
        # Scope risk to this case only: a new case has no correlations yet,
        # so never inherit adhoc (or other cases') scores via vessel_id.
        max_corr = _max_correlation(conn, case_id, None)
        risk = _risk_level(_case_score(body.candidate_confidence, max_corr))

        case_number = _next_case_number(conn)
        created_at = _now_z()
        conn.execute(
            "INSERT INTO investigation_cases "
            "(id, case_number, created_at, status, spill_id, "
            "candidate_confidence, origin_lat, origin_lon, "
            "origin_confidence, risk_level, selected_vessel_id, summary) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                case_id,
                case_number,
                created_at,
                "open",
                body.spill_id,
                body.candidate_confidence,
                body.origin_lat,
                body.origin_lon,
                body.origin_confidence,
                risk,
                body.selected_vessel_id,
                body.summary,
            ),
        )
        evidence_rows = [
            (
                "satellite observation",
                "Satellite observation",
                f"Sentinel-1 observation for {body.spill_id}",
                body.candidate_confidence,
                "sentinel-1",
            ),
            (
                "candidate",
                "Oil candidate",
                f"YOLO oil candidate {body.spill_id}",
                body.candidate_confidence,
                "yolo",
            ),
            (
                "origin",
                "Probable origin",
                f"Drift backtrack origin ({body.origin_lat}, {body.origin_lon})",
                body.origin_confidence,
                "hindcast",
            ),
        ]
        for ev_type, title, desc, conf, source in evidence_rows:
            conn.execute(
                "INSERT INTO case_evidence "
                "(case_id, evidence_type, title, description, confidence, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (case_id, ev_type, title, desc, conf, source),
            )
        conn.commit()
        row = conn.execute("SELECT * FROM investigation_cases WHERE id = ?", (case_id,)).fetchone()
        assert row is not None
        return _row_to_case_response(row)
    finally:
        conn.close()


@router.get("/cases", response_model=list[CaseResponse])
def list_cases(cfg: SettingsDep) -> list[CaseResponse]:
    """List investigation cases (excluding the adhoc correlation bucket)."""
    conn = _conn(cfg)
    try:
        rows = conn.execute(
            "SELECT * FROM investigation_cases WHERE case_number LIKE 'SIH-%' ORDER BY case_number"
        ).fetchall()
        return [_row_to_case_response(row) for row in rows]
    finally:
        conn.close()


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, cfg: SettingsDep) -> CaseDetail:
    """Return one case with vessel, correlations, evidence, and timeline."""
    conn = _conn(cfg)
    try:
        row = conn.execute("SELECT * FROM investigation_cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
        base = _row_to_case_response(row)

        vessel: Vessel | None = None
        if row["selected_vessel_id"] is not None:
            vrow = conn.execute(
                "SELECT * FROM vessels WHERE id = ?",
                (row["selected_vessel_id"],),
            ).fetchone()
            if vrow is not None:
                vessel = Vessel(
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

        corr_rows = conn.execute(
            "SELECT * FROM spill_vessel_correlations WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
        correlations: list[Any] = [dict(r) for r in corr_rows]
        ev_rows = conn.execute(
            "SELECT * FROM case_evidence WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
        evidence: list[Any] = [dict(r) for r in ev_rows]

        return CaseDetail(
            **base.model_dump(),
            vessel=vessel,
            correlations=correlations,
            evidence=evidence,
            timeline=_timeline(),
        )
    finally:
        conn.close()


__all__ = ["router"]
