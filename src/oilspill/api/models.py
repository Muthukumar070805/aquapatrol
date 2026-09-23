"""Pydantic request/response schemas for the YOLO inference API.

These mirror the JSON contract the frontend is built against exactly. Keeping the
schemas in one place lets FastAPI generate accurate OpenAPI docs at ``/docs`` and
gives the response handlers a single, typed source of truth.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# --- /healthz ----------------------------------------------------------------


class HealthResponse(BaseModel):
    """Liveness probe payload."""

    status: Literal["ok"] = "ok"


# --- /samples ----------------------------------------------------------------


class SampleInfo(BaseModel):
    """A preloaded sample image and the URL to fetch its bytes."""

    id: str
    url: str


class SamplesResponse(BaseModel):
    """List of preloaded sample images."""

    samples: list[SampleInfo]


# --- /jobs -------------------------------------------------------------------


class SceneJobRequest(BaseModel):
    """Request body for a YOLO scene detection job over an AOI/date range."""

    aoi: dict[str, Any]
    start: str
    end: str
    detector: Literal["yolo_mvp"] = "yolo_mvp"
    environmental_context: EnvironmentalContext | None = None


class EnvironmentalContext(BaseModel):
    """Optional environmental metadata supplied by the caller (not fetched)."""

    wind_speed_ms: float | None = None
    optical_corroboration: bool | None = None
    optical_conflict: bool | None = None


class SceneJobResponse(BaseModel):
    """Acknowledgement returned when a scene job is accepted."""

    job_id: str
    status: Literal["queued"] = "queued"


class JobResult(BaseModel):
    """Summary statistics + vectorised candidates of a finished scene job."""

    num_oil_polygons: int
    total_oil_area_km2: float
    geojson: dict[str, Any]
    yolo_result_image: str | None = None


class JobStatusResponse(BaseModel):
    """Current state of a scene job (polled by the frontend)."""

    job_id: str
    status: Literal["queued", "running", "done", "error"]
    detail: str | None = None
    result: JobResult | None = None


# --- YOLO single-image detection ----------------------------------------------


class YoloImageDetection(BaseModel):
    """One YOLO oil-candidate box in a single uploaded image."""

    spill_id: str
    bbox: list[int]
    confidence: float
    class_id: int
    class_name: str = "oil"
    tile_provenance: list[int] = Field(default_factory=list)


class YoloImageResponse(BaseModel):
    """YOLO result for a single uploaded image."""

    model_id: str
    width: int
    height: int
    num_candidates: int
    detections: list[YoloImageDetection]
    yolo_result_image: str


# --- YOLO status ---------------------------------------------------------------


class YoloStatusResponse(BaseModel):
    """YOLO detector availability status."""

    available: bool
    model_id: str | None = None
    detail: str


# --- Vessels --------------------------------------------------------------------


class Vessel(BaseModel):
    """One simulated-AIS vessel (investigation candidate context)."""

    id: str
    name: str
    mmsi: str
    imo: str
    flag: str
    vessel_type: str
    lat: float
    lon: float
    speed: float
    heading: float
    ais_status: str
    dark_vessel: bool
    last_seen: str
    source: Literal["simulated_ais"] = "simulated_ais"


class VesselTrackPoint(BaseModel):
    """One timestamped position of a vessel track."""

    timestamp: str
    lat: float
    lon: float
    speed: float
    heading: float


class VesselListResponse(BaseModel):
    """List of vessels plus the fixture source tag."""

    vessels: list[Vessel]
    source: Literal["simulated_ais"] = "simulated_ais"


# --- Correlations (investigative only) ------------------------------------------


CORRELATION_DISCLAIMER = (
    "Investigative correlation only — candidate vessel, "
    "requires verification. Not proof of responsibility."
)


class CorrelationRequest(BaseModel):
    """Request body for an investigative vessel correlation."""

    origin_lat: float
    origin_lon: float
    vessel_id: str
    trajectory_match: Literal["HIGH", "MED", "LOW"] = "HIGH"
    ais_visibility: Literal["FULL", "PARTIAL", "GAP"] = "PARTIAL"
    case_id: str | None = None
    detection_time: str | None = None


class CorrelationResponse(BaseModel):
    """Investigative correlation result for one candidate vessel."""

    vessel_id: str
    distance_km: float
    time_difference_hours: float
    trajectory_match: Literal["HIGH", "MED", "LOW"]
    ais_visibility: Literal["FULL", "PARTIAL", "GAP"]
    dark_vessel_indicator: bool
    correlation_score: float
    method: Literal["heuristic_v1"] = "heuristic_v1"
    disclaimer: str = CORRELATION_DISCLAIMER


# --- Cases (investigation cases, Task M5) ----------------------------------------


class CaseCreate(BaseModel):
    """Request body for opening an investigation case."""

    spill_id: str
    candidate_confidence: float
    origin_lat: float
    origin_lon: float
    origin_confidence: float
    selected_vessel_id: str | None = None
    summary: str | None = None


class CaseResponse(BaseModel):
    """One investigation case (list + create payload)."""

    id: str
    case_number: str
    status: str
    spill_id: str
    candidate_confidence: float
    origin_lat: float
    origin_lon: float
    origin_confidence: float
    risk_level: str
    selected_vessel_id: str | None = None
    summary: str | None = None
    created_at: str


class CaseDetail(CaseResponse):
    """Full case detail with joined vessel, correlations, evidence, timeline."""

    vessel: Vessel | None = None
    correlations: list[Any] = Field(default_factory=list)
    evidence: list[Any] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)


# --- Reports (on-screen incident report, Task M6) -------------------------------


REPORT_DISCLAIMER = (
    "Simulated demo data — requires verification. "
    "Investigative correlation only, not proof of responsibility."
)


class InvestigationSignal(BaseModel):
    """Heuristic investigation signal (not a probability)."""

    level: str
    score: float
    status: str


class ReportResponse(BaseModel):
    """On-screen incident report joining case, vessel, correlation, evidence."""

    case_id: str
    case_number: str
    observation_time: str
    spill_candidate: dict[str, Any]
    estimated_origin: dict[str, Any]
    vessel: Vessel | None = None
    correlation: dict[str, Any] | None = None
    evidence: list[Any] = Field(default_factory=list)
    investigation_signal: InvestigationSignal
    disclaimer: str = REPORT_DISCLAIMER


__all__ = [
    "CORRELATION_DISCLAIMER",
    "REPORT_DISCLAIMER",
    "CaseCreate",
    "CaseDetail",
    "CaseResponse",
    "CorrelationRequest",
    "CorrelationResponse",
    "EnvironmentalContext",
    "HealthResponse",
    "InvestigationSignal",
    "JobResult",
    "JobStatusResponse",
    "ReportResponse",
    "SampleInfo",
    "SamplesResponse",
    "SceneJobRequest",
    "SceneJobResponse",
    "Vessel",
    "VesselListResponse",
    "VesselTrackPoint",
    "YoloImageDetection",
    "YoloImageResponse",
    "YoloStatusResponse",
]
