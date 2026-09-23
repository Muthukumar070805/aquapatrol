"""FastAPI application factory for the YOLO oil-spill detection service.

Exposes a small JSON API plus static hosting for the built frontend:

* ``GET  /healthz``            -- liveness probe.
* ``GET  /samples``            -- preloaded sample images (list + bytes).
* ``GET  /samples/{name}``    -- raw sample image bytes.
* ``POST /yolo/detect``       -- YOLO candidate detection on one uploaded image.
* ``GET  /yolo/status``       -- YOLO detector availability.
* ``POST /jobs/scene``        -- queue a full-scene YOLO AOI detection job.
* ``GET  /jobs/{job_id}``     -- poll a scene job.
* ``POST /hindcast``          -- drift backtrack for one slick (no fetching).

The app degrades gracefully: missing YOLO weights yield a clear 503 instead of
a crash, and the static frontend is only mounted when ``web/dist`` exists.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from oilspill.api.cases import router as cases_router
from oilspill.api.correlations import router as correlations_router
from oilspill.api.models import (
    HealthResponse,
    JobStatusResponse,
    SampleInfo,
    SamplesResponse,
    SceneJobRequest,
    SceneJobResponse,
    YoloImageResponse,
    YoloStatusResponse,
)
from oilspill.api.reports import router as reports_router
from oilspill.api.service import JobStore, detect_yolo_image
from oilspill.api.settings import Settings, get_settings
from oilspill.api.vessels import router as vessels_router
from oilspill.hindcast import HindcastInput, run_hindcast

if TYPE_CHECKING:
    from oilspill.api.service import SceneRunner

# Image extensions exposed by the /samples endpoint.
_SAMPLE_EXTS = (".jpg", ".jpeg", ".png")


def _get_jobs(request: Request) -> JobStore:
    return request.app.state.jobs  # type: ignore[no-any-return]


def _get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


# Annotated dependency aliases (avoids `Depends()` in plain argument defaults).
JobsDep = Annotated[JobStore, Depends(_get_jobs)]
SettingsDep = Annotated[Settings, Depends(_get_settings_dep)]
UploadDep = Annotated[UploadFile, File(...)]


def _require_yolo(cfg: Settings) -> None:
    """Raise a 503 if the YOLO detector cannot run under ``cfg``."""
    from oilspill.detectors.yolo_detector import yolo_dependency_available

    if cfg.yolo_weights is None or not cfg.yolo_weights.exists():
        raise HTTPException(
            status_code=503,
            detail="YOLO detector unavailable: weights not configured. "
            "Set OILSPILL_API_YOLO_WEIGHTS to a valid checkpoint path.",
        )
    if not yolo_dependency_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "YOLO detector unavailable: optional dependency 'ultralytics' "
                "is not installed. Install the project's yolo extra."
            ),
        )


def create_app(
    settings: Settings | None = None,
    *,
    scene_runner: SceneRunner | None = None,
) -> FastAPI:
    """Build and return the configured FastAPI application.

    Parameters
    ----------
    settings:
        Optional pre-built settings; defaults to environment-resolved settings.
    scene_runner:
        Optional override for the scene-job runner (tests inject a fast mock to
        avoid network access and a real model).
    """
    settings = settings or get_settings()

    app = FastAPI(
        title="Oil Spill Detection API",
        version="0.2.0",
        description="Sentinel-1 SAR oil-spill candidate detection (YOLO).",
    )
    app.state.settings = settings
    app.state.jobs = JobStore(runner=scene_runner)
    app.include_router(vessels_router)
    app.include_router(correlations_router)
    app.include_router(cases_router)
    app.include_router(reports_router)

    @app.get("/healthz", response_model=HealthResponse, tags=["system"])
    def healthz() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/samples", response_model=SamplesResponse, tags=["samples"])
    def list_samples(cfg: SettingsDep) -> SamplesResponse:
        samples: list[SampleInfo] = []
        if cfg.samples_dir.exists():
            for path in sorted(cfg.samples_dir.iterdir()):
                if path.suffix.lower() in _SAMPLE_EXTS:
                    samples.append(SampleInfo(id=path.stem, url=f"/samples/{path.name}"))
        return SamplesResponse(samples=samples)

    @app.get("/samples/{name}", tags=["samples"])
    def get_sample(name: str, cfg: SettingsDep) -> FileResponse:
        # Guard against path traversal: only serve plain filenames from the dir.
        if "/" in name or "\\" in name or name in {"", ".", ".."}:
            raise HTTPException(status_code=400, detail="Invalid sample name.")
        path = cfg.samples_dir / name
        if not path.is_file() or path.suffix.lower() not in _SAMPLE_EXTS:
            raise HTTPException(status_code=404, detail=f"Sample not found: {name}")
        return FileResponse(path)

    @app.post("/yolo/detect", response_model=YoloImageResponse, tags=["yolo"])
    async def yolo_detect(file: UploadDep, cfg: SettingsDep) -> YoloImageResponse:
        _require_yolo(cfg)
        raw = await file.read()
        try:
            image = Image.open(io.BytesIO(raw))
            image.load()
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail="Could not read image.") from exc

        try:
            payload = detect_yolo_image(image, cfg)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return YoloImageResponse(**payload)

    @app.post("/jobs/scene", response_model=SceneJobResponse, tags=["jobs"])
    def create_scene_job(
        body: SceneJobRequest,
        background_tasks: BackgroundTasks,
        jobs: JobsDep,
        cfg: SettingsDep,
    ) -> SceneJobResponse:
        _require_yolo(cfg)
        job_id = jobs.create()
        env_ctx = (
            body.environmental_context.model_dump()
            if body.environmental_context is not None
            else None
        )
        background_tasks.add_task(
            jobs.run,
            job_id,
            body.aoi,
            body.start,
            body.end,
            env_context=env_ctx,
            settings=cfg,
        )
        return SceneJobResponse(job_id=job_id, status="queued")

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse, tags=["jobs"])
    def get_job(job_id: str, jobs: JobsDep) -> JobStatusResponse:
        status = jobs.status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        return status

    @app.get("/yolo/status", response_model=YoloStatusResponse, tags=["yolo"])
    def yolo_status(cfg: SettingsDep) -> YoloStatusResponse:
        from oilspill.detectors.yolo_detector import yolo_dependency_available

        dependency_available = yolo_dependency_available()
        available = (
            cfg.yolo_weights is not None and cfg.yolo_weights.exists() and dependency_available
        )
        model_id = cfg.yolo_weights.name if cfg.yolo_weights and available else None
        if available:
            detail = "YOLO detector ready (one-class oil candidate model)."
        elif cfg.yolo_weights is not None:
            detail = (
                "YOLO optional dependency is not installed. Install the project's yolo extra."
                if not dependency_available
                else "YOLO weights are configured but unavailable."
            )
        else:
            detail = "YOLO detector not configured (OILSPILL_API_YOLO_WEIGHTS unset)"
        return YoloStatusResponse(available=available, model_id=model_id, detail=detail)

    @app.post("/hindcast", tags=["hindcast"])
    def perform_hindcast(body: HindcastInput) -> dict:
        result = run_hindcast(body)
        return {
            "json": result.to_dict(),
            "geojson": result.to_geojson(),
        }

    # Mount the built frontend last so the API routes above take precedence; only
    # if it exists, so the API still serves standalone with client-side SPA routing.
    if settings.web_dist.exists():
        from starlette.exceptions import HTTPException as StarletteHTTPException

        class SPAStaticFiles(StaticFiles):
            async def get_response(self, path: str, scope: Any) -> Any:
                try:
                    response = await super().get_response(path, scope)
                except (HTTPException, StarletteHTTPException) as ex:
                    if ex.status_code == 404:
                        return await super().get_response("index.html", scope)
                    raise
                if response.status_code == 404:
                    return await super().get_response("index.html", scope)
                return response

        app.mount("/", SPAStaticFiles(directory=settings.web_dist, html=True), name="web")

    return app


__all__ = ["create_app"]
