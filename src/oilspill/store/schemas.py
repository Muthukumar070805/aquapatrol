"""Light Pydantic models mirroring the prototype store rows."""

from __future__ import annotations

from pydantic import BaseModel


class InvestigationCase(BaseModel):
    """Row in the ``investigation_cases`` table."""

    id: str | None = None
    case_number: str | None = None
    created_at: str | None = None
    status: str | None = None
    spill_id: str | None = None
    candidate_confidence: float | None = None
    origin_lat: float | None = None
    origin_lon: float | None = None
    origin_confidence: float | None = None
    risk_level: str | None = None
    selected_vessel_id: str | None = None
    summary: str | None = None


class Vessel(BaseModel):
    """Row in the ``vessels`` table."""

    id: str | None = None
    name: str | None = None
    mmsi: str | None = None
    imo: str | None = None
    flag: str | None = None
    vessel_type: str | None = None
    lat: float | None = None
    lon: float | None = None
    speed: float | None = None
    heading: float | None = None
    ais_status: str | None = None
    dark_vessel: int | None = None
    last_seen: str | None = None


class VesselTrack(BaseModel):
    """Row in the ``vessel_tracks`` table."""

    id: int | None = None
    vessel_id: str | None = None
    timestamp: str | None = None
    lat: float | None = None
    lon: float | None = None
    speed: float | None = None
    heading: float | None = None


class SpillVesselCorrelation(BaseModel):
    """Row in the ``spill_vessel_correlations`` table."""

    id: int | None = None
    case_id: str | None = None
    vessel_id: str | None = None
    distance_km: float | None = None
    time_difference_hours: float | None = None
    trajectory_match: str | None = None
    dark_vessel_indicator: int | None = None
    correlation_score: float | None = None


class CaseEvidence(BaseModel):
    """Row in the ``case_evidence`` table."""

    id: int | None = None
    case_id: str | None = None
    evidence_type: str | None = None
    title: str | None = None
    description: str | None = None
    confidence: float | None = None
    source: str | None = None


__all__ = [
    "CaseEvidence",
    "InvestigationCase",
    "SpillVesselCorrelation",
    "Vessel",
    "VesselTrack",
]
