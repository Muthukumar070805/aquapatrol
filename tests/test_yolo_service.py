"""Tests for the YOLO service layer and pipeline download helpers.

All heavy boundaries (weights loading, CDSE search/download, SAFE reading) are
faked, so the suite stays offline and fast while covering the real orchestration
code in :mod:`oilspill.api.service` and :mod:`oilspill.pipeline.detect`.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from affine import Affine
from PIL import Image
from rasterio.crs import CRS

from oilspill.api import service as svc
from oilspill.api.models import JobResult
from oilspill.api.settings import Settings
from oilspill.pipeline import detect as pipeline_detect

# --- fakes -------------------------------------------------------------------


class _FakeTensor:
    def __init__(self, value: object) -> None:
        self.value = np.asarray(value)

    def cpu(self) -> _FakeTensor:
        return self

    def numpy(self) -> np.ndarray:
        return self.value


class _FakeBoxes:
    def __init__(self, xyxy: list[list[float]], confidence: list[float]) -> None:
        self.xyxy = [_FakeTensor(box) for box in xyxy]
        self.conf = [_FakeTensor(value) for value in confidence]
        self.cls = [_FakeTensor(0) for _ in xyxy]

    def __len__(self) -> int:
        return len(self.xyxy)


class _FakeResult:
    def __init__(self, boxes: _FakeBoxes) -> None:
        self.boxes = boxes


class _OneBoxModel:
    """Fake Ultralytics model returning one box per tile."""

    def predict(self, _crop: np.ndarray, **_kwargs: object) -> list[_FakeResult]:
        return [_FakeResult(_FakeBoxes([[10, 10, 50, 50]], [0.8]))]


@pytest.fixture
def weights(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "best.pt"
    path.write_bytes(b"test-only")
    monkeypatch.setattr("oilspill.detectors.yolo_detector.yolo_dependency_available", lambda: True)
    return path


@pytest.fixture
def settings(tmp_path: Path, weights: Path) -> Settings:
    return Settings(
        samples_dir=tmp_path / "samples",
        scenes_dir=tmp_path / "scenes",
        web_dist=tmp_path / "no-web",
        yolo_weights=weights,
    )


# --- detector construction ----------------------------------------------------


def test_build_detector_config_maps_settings(settings: Settings, weights: Path) -> None:
    cfg = svc.build_detector_config(settings)
    assert cfg.weights_path == weights
    assert cfg.conf_threshold == settings.yolo_conf_threshold
    assert cfg.tile_size == settings.yolo_tile_size
    assert (cfg.db_min, cfg.db_max) == (settings.yolo_db_min, settings.yolo_db_max)


def test_get_detector_is_lazy(settings: Settings) -> None:
    detector = svc.get_detector(settings)
    assert detector.config.weights_path == settings.yolo_weights
    assert detector._model is None


# --- single-image detection ----------------------------------------------------


def test_detect_yolo_image_returns_candidates(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "oilspill.detectors.yolo_detector.YoloDetector._load_model",
        lambda self: _OneBoxModel(),
    )
    rng = np.random.default_rng(0)
    image = Image.fromarray(rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8), mode="RGB")
    payload = svc.detect_yolo_image(image, settings)
    assert payload["model_id"] == "best.pt"
    assert (payload["width"], payload["height"]) == (64, 64)
    assert payload["num_candidates"] == 1
    det = payload["detections"][0]
    assert det["spill_id"] == "SPILL_001"
    assert det["bbox"] == [10, 10, 50, 50]
    assert det["confidence"] == pytest.approx(0.8)
    assert det["class_name"] == "oil"
    assert payload["yolo_result_image"].startswith("data:image/png;base64,")


def test_detect_yolo_image_empty_when_no_boxes(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _EmptyModel:
        def predict(self, _crop: np.ndarray, **_kwargs: object) -> list[Any]:
            return []

    monkeypatch.setattr(
        "oilspill.detectors.yolo_detector.YoloDetector._load_model",
        lambda self: _EmptyModel(),
    )
    image = Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8), mode="RGB")
    payload = svc.detect_yolo_image(image, settings)
    assert payload["num_candidates"] == 0
    assert payload["detections"] == []


def test_detect_yolo_image_missing_weights_raises(tmp_path: Path) -> None:
    cfg = Settings(
        samples_dir=tmp_path / "samples",
        web_dist=tmp_path / "no-web",
        yolo_weights=tmp_path / "missing.pt",
    )
    image = Image.fromarray(np.zeros((16, 16, 3), dtype=np.uint8), mode="RGB")
    with pytest.raises(FileNotFoundError):
        svc.detect_yolo_image(image, cfg)


# --- scene-job runner -----------------------------------------------------------


def _fake_scene() -> SimpleNamespace:
    return SimpleNamespace(
        sigma0=np.full((100, 100), -12.0, dtype=np.float32),
        transform=Affine(10.0, 0.0, 500000.0, 0.0, -10.0, 4000000.0),
        crs=CRS.from_epsg(32631),
    )


def test_run_yolo_detection_builds_geojson_result(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "oilspill.pipeline.detect._download_safe_for_aoi",
        lambda *a, **k: tmp_path / "scene.SAFE",
    )
    monkeypatch.setattr(
        "oilspill.pipeline.preprocess.read_grd_measurement",
        lambda *a, **k: _fake_scene(),
    )
    monkeypatch.setattr(
        "oilspill.detectors.yolo_detector.YoloDetector._load_model",
        lambda self: _OneBoxModel(),
    )
    aoi: dict[str, Any] = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
    }
    result = svc._run_yolo_detection(aoi, "2024-01-01", "2024-01-31", settings, None)
    assert isinstance(result, JobResult)
    assert result.num_oil_polygons == 1
    features = result.geojson["features"]
    assert features[0]["properties"]["spill_id"] == "SPILL_001"
    assert features[0]["properties"]["detector_type"] == "yolo_mvp"
    assert result.geojson["metadata"]["model_id"] == "best.pt"
    assert result.yolo_result_image is not None
    assert result.yolo_result_image.startswith("data:image/png;base64,")


def test_run_yolo_detection_missing_weights_raises(tmp_path: Path) -> None:
    cfg = Settings(
        samples_dir=tmp_path / "samples",
        web_dist=tmp_path / "no-web",
        yolo_weights=tmp_path / "missing.pt",
    )
    with pytest.raises(FileNotFoundError):
        svc._run_yolo_detection({}, "2024-01-01", "2024-01-31", cfg, None)


def test_jobstore_create_status_and_unknown() -> None:
    def _runner(*args: object, **kwargs: object) -> JobResult:
        return JobResult(num_oil_polygons=0, total_oil_area_km2=0.0, geojson={})

    store = svc.JobStore(runner=_runner)
    job_id = store.create()
    created = store.status(job_id)
    assert created is not None
    assert created.status == "queued"
    assert store.status("nope") is None
    # Unknown jobs are ignored, failing jobs capture the error.
    store.run("ghost", {}, "2024-01-01", "2024-01-31", settings=None)
    failing = svc.JobStore(runner=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    fid = failing.create()
    failing.run(fid, {}, "2024-01-01", "2024-01-31", settings=None)
    failed = failing.status(fid)
    assert failed is not None
    assert failed.status == "error"


# --- pipeline download helpers --------------------------------------------------


def _write_aoi(path: Path) -> Path:
    import json

    path.write_text(
        json.dumps({"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]}),
        encoding="utf-8",
    )
    return path


def test_download_safe_for_aoi_uses_cached_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cached = tmp_path / "safe" / "P.SAFE"
    (cached).mkdir(parents=True)
    (cached / "manifest.safe").write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        "oilspill.pipeline.ingest.search_products",
        lambda *a, **k: [SimpleNamespace(name="P")],
    )
    got = pipeline_detect._download_safe_for_aoi(
        _write_aoi(tmp_path / "aoi.geojson"),
        "2024-01-01",
        "2024-01-31",
        tmp_path / "out",
        download_dir=tmp_path / "safe",
    )
    assert got == cached


def test_download_safe_for_aoi_no_products_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("oilspill.pipeline.ingest.search_products", lambda *a, **k: [])
    with pytest.raises(RuntimeError, match="No Sentinel-1 scenes"):
        pipeline_detect._download_safe_for_aoi(
            _write_aoi(tmp_path / "aoi.geojson"),
            "2024-01-01",
            "2024-01-31",
            tmp_path / "out",
            download_dir=tmp_path / "safe",
        )


def test_detect_yolo_from_aoi_wires_download_and_detect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from oilspill.detectors.yolo_detector import YoloDetector, YoloDetectorConfig

    seen: dict[str, object] = {}

    def _fake_download(*args: object, **kwargs: object) -> Path:
        seen["args"] = args
        return tmp_path / "scene.SAFE"

    def _fake_detect(safe_path: Path | str, detector: YoloDetector, **kwargs: object) -> str:
        seen["safe"] = safe_path
        return "ok"

    monkeypatch.setattr(pipeline_detect, "_download_safe_for_aoi", _fake_download)
    monkeypatch.setattr(pipeline_detect, "detect_yolo_from_safe", _fake_detect)
    detector = YoloDetector(YoloDetectorConfig(weights_path=tmp_path / "w.pt"))
    out = pipeline_detect.detect_yolo_from_aoi(
        tmp_path / "aoi.geojson", "2024-01-01", "2024-01-31", detector, tmp_path / "out"
    )
    assert out == "ok"
    assert seen["safe"] == tmp_path / "scene.SAFE"


# --- frontend contract parity ---------------------------------------------------


def test_single_image_payload_matches_response_schema(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`detect_yolo_image()` keys must equal `YoloImageResponse` fields.

    The frontend (`QuickDetect`) reads `yolo_result_image`, `detections`, and
    `num_candidates`; any shape drift must fail here, not in the browser.
    """
    from oilspill.api.models import YoloImageDetection, YoloImageResponse

    monkeypatch.setattr(
        "oilspill.detectors.yolo_detector.YoloDetector._load_model",
        lambda self: _OneBoxModel(),
    )
    image = Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8), mode="RGB")
    payload = svc.detect_yolo_image(image, settings)
    assert set(payload) == set(YoloImageResponse.model_fields)
    assert set(payload["detections"][0]) == set(YoloImageDetection.model_fields)
    # Round-trips through the response model (what FastAPI validates).
    parsed = YoloImageResponse(**payload)
    assert parsed.detections[0].spill_id == "SPILL_001"


def test_scene_job_geojson_matches_frontend_reads(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Scene features must carry every property `SceneMonitor` renders."""
    monkeypatch.setattr(
        "oilspill.pipeline.detect._download_safe_for_aoi",
        lambda *a, **k: tmp_path / "scene.SAFE",
    )
    monkeypatch.setattr(
        "oilspill.pipeline.preprocess.read_grd_measurement",
        lambda *a, **k: _fake_scene(),
    )
    monkeypatch.setattr(
        "oilspill.detectors.yolo_detector.YoloDetector._load_model",
        lambda self: _OneBoxModel(),
    )
    aoi: dict[str, Any] = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
    }
    result = svc._run_yolo_detection(aoi, "2024-01-01", "2024-01-31", settings, None)
    props = result.geojson["features"][0]["properties"]
    for key in ("spill_id", "confidence", "latitude", "longitude", "class_name", "bbox"):
        assert key in props, f"SceneMonitor reads missing property: {key}"
    assert isinstance(result.yolo_result_image, str)
