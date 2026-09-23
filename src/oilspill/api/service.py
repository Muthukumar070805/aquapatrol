"""Service layer: YOLO detector wiring, single-image detection and scene jobs.

This module holds all the non-HTTP logic the route handlers delegate to, so the
FastAPI layer (``app.py``) stays a thin adapter:

* :func:`get_detector` builds a :class:`YoloDetector` from the resolved settings.
* :func:`detect_yolo_image` runs the single-upload path: PIL -> grayscale uint8
  -> stacked RGB -> :func:`run_tiled_yolo` -> annotated preview (base64 PNG) +
  per-box candidate records.
* :class:`JobStore` is an in-process registry of background scene jobs (a plain
  dict guarded by a lock); jobs run on FastAPI ``BackgroundTasks`` threads. No
  external broker is involved.
"""

from __future__ import annotations

import base64
import io
import json
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image

from oilspill.api.models import JobResult, JobStatusResponse

if TYPE_CHECKING:
    from oilspill.api.settings import Settings
    from oilspill.detectors.yolo_detector import YoloDetector, YoloDetectorConfig


# --- detector construction ----------------------------------------------------


def build_detector_config(settings: Settings) -> YoloDetectorConfig:
    """Translate API settings into a :class:`YoloDetectorConfig`."""
    from oilspill.detectors.yolo_detector import YoloDetectorConfig

    return YoloDetectorConfig(
        weights_path=settings.yolo_weights,
        conf_threshold=settings.yolo_conf_threshold,
        iou_threshold=settings.yolo_iou_threshold,
        tile_size=settings.yolo_tile_size,
        tile_overlap=settings.yolo_tile_overlap,
        db_min=settings.yolo_db_min,
        db_max=settings.yolo_db_max,
        contour_min_pixels=settings.yolo_contour_min_pixels,
        morph_size=settings.yolo_contour_morph_size,
        simplify_tolerance=settings.yolo_contour_simplify_tolerance,
        low_wind_threshold=settings.yolo_low_wind_threshold,
    )


def get_detector(settings: Settings) -> YoloDetector:
    """Build a YOLO detector from ``settings`` (weights load lazily)."""
    from oilspill.detectors.yolo_detector import YoloDetector

    return YoloDetector(build_detector_config(settings))


def _png_data_uri(rgb: np.ndarray) -> str:
    """Encode an ``HxWx3`` uint8 RGB array as a base64 PNG ``data:`` URI."""
    buf = io.BytesIO()
    Image.fromarray(rgb.astype(np.uint8), mode="RGB").save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def annotate_yolo_image(yolo_image: np.ndarray, detections: list[Any], max_dim: int = 1600) -> str:
    """Draw bounding boxes and confidence labels on the YOLO image and return a data URI."""
    import cv2

    img = yolo_image.copy()
    for det in detections:
        cv2.rectangle(img, (det.x1, det.y1), (det.x2, det.y2), (255, 0, 0), 2)
        label = f"oil {det.confidence:.2f}"
        cv2.putText(
            img, label, (det.x1, max(det.y1 - 5, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1
        )

    # Downsample large scenes for web preview so base64 payload is responsive (< 1MB)
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return _png_data_uri(img)


# --- single-image detection ----------------------------------------------------


def detect_yolo_image(
    image: Image.Image,
    settings: Settings,
) -> dict[str, Any]:
    """Run YOLO candidate detection on one uploaded image.

    Uploaded images are plain RGB chips (like the committed samples), not
    calibrated SAR scenes, so they are grayscaled directly to the 8-bit RGB
    rendering YOLO expects instead of going through the dB chain.

    Returns a plain dict matching :class:`oilspill.api.models.YoloImageResponse`.
    """
    from oilspill.detectors.yolo_detector import run_tiled_yolo

    detector = get_detector(settings)
    model = detector._load_model()
    config = detector.config
    model_id = str(config.weights_path.name) if config.weights_path else "yolo_mvp"

    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    gray = rgb.mean(axis=2).astype(np.uint8)
    yolo_image = np.stack([gray, gray, gray], axis=-1)

    detections = run_tiled_yolo(
        model,
        yolo_image,
        tile_size=config.tile_size,
        tile_overlap=config.tile_overlap,
        conf=config.conf_threshold,
        iou=config.iou_threshold,
    )

    records = [
        {
            "spill_id": f"SPILL_{i + 1:03d}",
            "bbox": [det.x1, det.y1, det.x2, det.y2],
            "confidence": det.confidence,
            "class_id": det.class_id,
            "class_name": "oil",
            "tile_provenance": det.tile_indices or [det.tile_index],
        }
        for i, det in enumerate(detections)
    ]

    return {
        "model_id": model_id,
        "width": width,
        "height": height,
        "num_candidates": len(records),
        "detections": records,
        "yolo_result_image": annotate_yolo_image(yolo_image, detections),
    }


# --- scene jobs ---------------------------------------------------------------


@dataclass
class _Job:
    """Internal mutable state of one scene-detection job."""

    job_id: str
    status: str = "queued"
    detail: str | None = None
    result: JobResult | None = None
    detector: str = "yolo_mvp"
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


# Type of the callable that performs the actual detection. Injected so tests can
# substitute a fast mock for the network-bound real pipeline.
SceneRunner = Any


class JobStore:
    """In-process registry of background YOLO scene jobs (dict + lock, no broker).

    Jobs are created in the ``queued`` state, moved to ``running`` when the
    background task starts, and end in ``done`` or ``error``. State lives only in
    this process for the life of the server, which is what the single-container
    deployment needs.
    """

    def __init__(self, runner: SceneRunner | None = None) -> None:
        self._jobs: dict[str, _Job] = {}
        self._lock = threading.Lock()
        self._runner: SceneRunner = runner if runner is not None else _run_yolo_detection

    def create(self) -> str:
        """Register a new queued job and return its id."""
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = _Job(job_id=job_id)
        return job_id

    def _get(self, job_id: str) -> _Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def status(self, job_id: str) -> JobStatusResponse | None:
        """Return the current status of ``job_id`` (or ``None`` if unknown)."""
        job = self._get(job_id)
        if job is None:
            return None
        with job._lock:
            return JobStatusResponse(
                job_id=job.job_id,
                status=job.status,  # type: ignore[arg-type]
                detail=job.detail,
                result=job.result,
            )

    def run(
        self,
        job_id: str,
        aoi: dict[str, Any],
        start: str,
        end: str,
        *,
        env_context: dict[str, Any] | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Execute one job to completion (intended to run on a background thread).

        Any failure is captured into the job's ``error`` state with a message,
        rather than propagated, so a failing job never crashes the server.
        """
        job = self._get(job_id)
        if job is None:
            return
        with job._lock:
            job.status = "running"
        try:
            result = self._runner(aoi, start, end, settings, env_context)
            with job._lock:
                job.status = "done"
                job.result = result
        except Exception as exc:  # surface any failure as job error, never crash
            with job._lock:
                job.status = "error"
                job.detail = str(exc)


def _run_yolo_detection(
    aoi: dict[str, Any],
    start: str,
    end: str,
    settings: Settings,
    env_context: dict[str, Any] | None = None,
) -> JobResult:
    """Run a full CDSE -> SAFE -> filtered-dB -> YOLO MVP scene job."""
    import tempfile

    from shapely.geometry import shape as shapely_shape

    from oilspill.detectors.yolo_detector import (
        YoloDetector,
        YoloDetectorConfig,
        bbox_to_polygon,
        geometry_to_wgs84_geojson,
        run_tiled_yolo,
        sar_to_yolo_image,
        yolo_dependency_available,
    )
    from oilspill.pipeline.detect import _download_safe_for_aoi
    from oilspill.pipeline.preprocess import (
        calibrate_safe,
        lee_filter,
        read_grd_measurement,
        to_db,
    )

    if settings.yolo_weights is None or not settings.yolo_weights.exists():
        raise FileNotFoundError(
            "YOLO detector unavailable: weights not configured. "
            "Set OILSPILL_API_YOLO_WEIGHTS to a valid checkpoint path."
        )
    if not yolo_dependency_available():
        raise RuntimeError(
            "YOLO detector unavailable: optional dependency 'ultralytics' is not installed. "
            "Install the project's yolo extra."
        )

    config = YoloDetectorConfig(
        weights_path=settings.yolo_weights,
        conf_threshold=settings.yolo_conf_threshold,
        iou_threshold=settings.yolo_iou_threshold,
        tile_size=settings.yolo_tile_size,
        tile_overlap=settings.yolo_tile_overlap,
        db_min=settings.yolo_db_min,
        db_max=settings.yolo_db_max,
        contour_min_pixels=settings.yolo_contour_min_pixels,
        morph_size=settings.yolo_contour_morph_size,
        simplify_tolerance=settings.yolo_contour_simplify_tolerance,
        low_wind_threshold=settings.yolo_low_wind_threshold,
    )
    detector = YoloDetector(config)
    model = detector._load_model()
    model_id = str(config.weights_path.name) if config.weights_path else "yolo_mvp"

    # Extract bounding box from AOI for windowed reading
    bbox: tuple[float, float, float, float] | None = None
    try:
        geom = aoi.get("geometry", aoi)
        coords = geom.get("coordinates", [[]])[0]
        if coords:
            lons = [float(pt[0]) for pt in coords]
            lats = [float(pt[1]) for pt in coords]
            pad = 0.02
            bbox = (min(lons) - pad, min(lats) - pad, max(lons) + pad, max(lats) + pad)
    except Exception:
        bbox = None

    with tempfile.TemporaryDirectory(prefix="oilspill-yolo-scene-") as tmp:
        out_dir = Path(tmp)
        aoi_path = out_dir / "aoi.geojson"
        aoi_path.write_text(json.dumps(aoi), encoding="utf-8")

        safe_path = _download_safe_for_aoi(
            aoi_path,
            start,
            end,
            out_dir,
            download_dir=settings.scenes_dir,
        )

        # Fast path: read only the requested AOI bounding box using GCP windowed read
        scene = None
        if bbox is not None:
            try:
                scene = read_grd_measurement(safe_path, polarisation="vv", bbox=bbox)
            except Exception:
                scene = None

        if scene is None:
            scene = calibrate_safe(safe_path, polarisation="vv")

        filtered = lee_filter(scene.sigma0, size=7)
        db = to_db(filtered)

    yolo_image = sar_to_yolo_image(db, db_min=config.db_min, db_max=config.db_max)
    detections = run_tiled_yolo(
        model,
        yolo_image,
        tile_size=config.tile_size,
        tile_overlap=config.tile_overlap,
        conf=config.conf_threshold,
        iou=config.iou_threshold,
    )

    yolo_result_image = annotate_yolo_image(yolo_image, detections)

    features: list[dict[str, Any]] = []

    for i, det in enumerate(detections):
        spill_id = f"SPILL_{i + 1:03d}"

        # Bbox in WGS84 GeoJSON
        bbox_geojson = bbox_to_polygon(det.x1, det.y1, det.x2, det.y2, scene.transform)
        wgs84_geojson = geometry_to_wgs84_geojson(shapely_shape(bbox_geojson), scene.crs)

        centroid_shapely = shapely_shape(wgs84_geojson).centroid
        lon, lat = centroid_shapely.x, centroid_shapely.y

        features.append(
            {
                "type": "Feature",
                "geometry": wgs84_geojson,
                "properties": {
                    "spill_id": spill_id,
                    "latitude": lat,
                    "longitude": lon,
                    "bbox": [det.x1, det.y1, det.x2, det.y2],
                    "confidence": det.confidence,
                    "model_confidence": det.confidence,
                    "class_id": det.class_id,
                    "class_name": "oil",
                    "detector_type": "yolo_mvp",
                    "model_id": model_id,
                    "tile_provenance": det.tile_indices or [det.tile_index],
                },
            }
        )

    scene_geom = shapely_shape(bbox_to_polygon(0, 0, db.shape[1], db.shape[0], scene.transform))
    scene_wgs84 = geometry_to_wgs84_geojson(scene_geom, scene.crs)
    scene_bbox = list(shapely_shape(scene_wgs84).bounds)

    return JobResult(
        num_oil_polygons=len(features),
        total_oil_area_km2=0.0,
        geojson={
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "detector": "yolo_mvp",
                "model_id": model_id,
                "scene_id": Path(safe_path).stem,
                "scene_crs": str(scene.crs),
                "scene_bbox": scene_bbox,
                "image_width": db.shape[1],
                "image_height": db.shape[0],
                "scene_metadata": {
                    "tile_size": config.tile_size,
                    "tile_overlap": config.tile_overlap,
                    "conf_threshold": config.conf_threshold,
                    "iou_threshold": config.iou_threshold,
                },
            },
        },
        yolo_result_image=yolo_result_image,
    )


__all__ = [
    "JobStore",
    "SceneRunner",
    "annotate_yolo_image",
    "build_detector_config",
    "detect_yolo_image",
    "get_detector",
]
