"""Tests for the YOLO FastAPI service (:mod:`oilspill.api`).

The suite is fully offline: the Ultralytics dependency and the CDSE-bound scene
runner are monkeypatched, so the whole module runs in seconds with no weights
and no network.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from oilspill.api.app import create_app
from oilspill.api.models import JobResult
from oilspill.api.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Iterator


# --- fixtures ----------------------------------------------------------------


@pytest.fixture
def env(tmp_path: Path) -> Settings:
    """A self-contained Settings pointing at temp samples/scenes dirs."""
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()

    # A couple of small sample images.
    for i in (1, 2):
        img = Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8), mode="RGB")
        img.save(samples_dir / f"sample_0{i}.png")

    return Settings(
        samples_dir=samples_dir,
        scenes_dir=tmp_path / "scenes",
        web_dist=tmp_path / "no-web",  # absent -> static mount skipped
        yolo_weights=tmp_path / "missing.pt",  # absent -> YOLO 503 paths
    )


def _mock_runner(
    aoi: dict[str, Any],
    start: str,
    end: str,
    settings: Settings | None,
    env_context: dict[str, Any] | None = None,
) -> JobResult:
    return JobResult(
        num_oil_polygons=2,
        total_oil_area_km2=0.0,
        geojson={"type": "FeatureCollection", "features": []},
    )


@pytest.fixture
def client(env: Settings) -> Iterator[TestClient]:
    app = create_app(env, scene_runner=_mock_runner)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def yolo_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings with a present (fake) weights file and patched dependency."""
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"test-only")
    monkeypatch.setattr("oilspill.detectors.yolo_detector.yolo_dependency_available", lambda: True)
    return Settings(
        samples_dir=tmp_path / "samples",
        scenes_dir=tmp_path / "scenes",
        web_dist=tmp_path / "no-web",
        yolo_weights=weights,
    )


# --- /healthz ----------------------------------------------------------------


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- /samples ----------------------------------------------------------------


def test_samples_list_and_serve(client: TestClient) -> None:
    resp = client.get("/samples")
    assert resp.status_code == 200
    samples = resp.json()["samples"]
    assert {s["id"] for s in samples} == {"sample_01", "sample_02"}

    url = samples[0]["url"]
    assert url.startswith("/samples/")
    img_resp = client.get(url)
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"].startswith("image/")


def test_sample_not_found(client: TestClient) -> None:
    assert client.get("/samples/nope.png").status_code == 404


def test_sample_traversal_rejected(client: TestClient) -> None:
    # Encoded traversal resolves to a name with a slash -> rejected as 400/404.
    assert client.get("/samples/..%2Fsecret.txt").status_code in {400, 404}


# --- /yolo/detect -------------------------------------------------------------


def _png_upload(size: int = 64) -> bytes:
    rng = np.random.default_rng(0)
    arr = rng.integers(0, 256, size=(size, size, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def test_yolo_detect_503_without_weights(client: TestClient) -> None:
    files = {"file": ("test.png", _png_upload(), "image/png")}
    resp = client.post("/yolo/detect", files=files)
    assert resp.status_code == 503
    assert "OILSPILL_API_YOLO_WEIGHTS" in resp.text


def test_yolo_detect_503_without_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"test-only")
    monkeypatch.setattr("oilspill.detectors.yolo_detector.yolo_dependency_available", lambda: False)
    cfg = Settings(
        samples_dir=tmp_path / "samples",
        web_dist=tmp_path / "no-web",
        yolo_weights=weights,
    )
    app = create_app(cfg)
    with TestClient(app) as c:
        files = {"file": ("test.png", _png_upload(), "image/png")}
        resp = c.post("/yolo/detect", files=files)
    assert resp.status_code == 503
    assert str(weights) not in resp.text


def test_yolo_detect_bad_image(yolo_env: Settings) -> None:
    app = create_app(yolo_env)
    with TestClient(app) as c:
        files = {"file": ("bad.png", b"not an image", "image/png")}
        assert c.post("/yolo/detect", files=files).status_code == 400


def test_yolo_detect_returns_candidates(
    yolo_env: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "model_id": "best.pt",
        "width": 64,
        "height": 64,
        "num_candidates": 1,
        "detections": [
            {
                "spill_id": "SPILL_001",
                "bbox": [10, 10, 50, 50],
                "confidence": 0.8,
                "class_id": 0,
                "class_name": "oil",
                "tile_provenance": [0],
            }
        ],
        "yolo_result_image": "data:image/png;base64,mockbase64",
    }
    monkeypatch.setattr("oilspill.api.app.detect_yolo_image", lambda image, settings: payload)
    app = create_app(yolo_env)
    with TestClient(app) as c:
        files = {"file": ("test.png", _png_upload(), "image/png")}
        resp = c.post("/yolo/detect", files=files)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model_id"] == "best.pt"
    assert body["num_candidates"] == 1
    assert body["detections"][0]["spill_id"] == "SPILL_001"
    assert body["yolo_result_image"].startswith("data:image/png;base64,")


def test_legacy_predict_gone(client: TestClient) -> None:
    files = {"file": ("test.png", _png_upload(), "image/png")}
    assert client.post("/predict", files=files).status_code == 404


def test_legacy_models_gone(client: TestClient) -> None:
    assert client.get("/models").status_code == 404


# --- /jobs -------------------------------------------------------------------


def test_scene_job_requires_yolo(client: TestClient) -> None:
    body = {
        "aoi": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        "start": "2024-01-01",
        "end": "2024-01-31",
    }
    assert client.post("/jobs/scene", json=body).status_code == 503


def test_scene_job_lifecycle(yolo_env: Settings) -> None:
    app = create_app(yolo_env, scene_runner=_mock_runner)
    body = {
        "aoi": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        "start": "2024-01-01",
        "end": "2024-01-31",
        "environmental_context": {"wind_speed_ms": 2.0},
    }
    with TestClient(app) as c:
        resp = c.post("/jobs/scene", json=body)
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "queued"
        job_id = payload["job_id"]

        # TestClient runs BackgroundTasks synchronously after the response, so by
        # the time we poll the job has reached a terminal state.
        status = c.get(f"/jobs/{job_id}").json()
    assert status["status"] == "done"
    assert status["result"]["num_oil_polygons"] == 2


def test_yolo_status_and_scene_job_result(
    yolo_env: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configured YOLO job uses the candidate GeoJSON result path."""

    def _fake_yolo(
        _aoi: dict[str, Any],
        _start: str,
        _end: str,
        _settings: Settings | None,
        _ctx: dict[str, Any] | None = None,
    ) -> JobResult:
        return JobResult(
            num_oil_polygons=1,
            total_oil_area_km2=0.0,
            geojson={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[1.0, 1.0], [1.1, 1.0], [1.1, 1.1], [1.0, 1.0]]],
                        },
                        "properties": {
                            "spill_id": "SPILL_001",
                            "latitude": 1.05,
                            "longitude": 1.05,
                            "bbox": [10, 10, 50, 50],
                            "confidence": 0.8,
                            "model_confidence": 0.8,
                            "class_id": 0,
                            "class_name": "oil",
                            "detector_type": "yolo_mvp",
                            "model_id": "best.pt",
                            "tile_provenance": [0],
                        },
                    }
                ],
            },
            yolo_result_image="data:image/png;base64,mockbase64",
        )

    monkeypatch.setattr("oilspill.api.service._run_yolo_detection", _fake_yolo)
    app = create_app(yolo_env)
    body = {
        "aoi": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        "start": "2024-01-01",
        "end": "2024-01-31",
        "detector": "yolo_mvp",
        "environmental_context": {"wind_speed_ms": 2.0},
    }
    with TestClient(app) as c:
        assert c.get("/yolo/status").json()["available"] is True
        job_id = c.post("/jobs/scene", json=body).json()["job_id"]
        status = c.get(f"/jobs/{job_id}").json()
    assert status["status"] == "done"
    assert status["result"]["num_oil_polygons"] == 1
    props = status["result"]["geojson"]["features"][0]["properties"]
    assert props["detector_type"] == "yolo_mvp"
    assert props["spill_id"] == "SPILL_001"
    assert status["result"]["yolo_result_image"].startswith("data:image/png;base64,")


def test_yolo_dependency_missing_is_not_advertised_as_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"test-only")
    monkeypatch.setattr("oilspill.detectors.yolo_detector.yolo_dependency_available", lambda: False)
    cfg = Settings(
        samples_dir=tmp_path / "samples",
        web_dist=tmp_path / "no-web",
        yolo_weights=weights,
    )
    app = create_app(cfg)
    body = {
        "aoi": {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        "start": "2024-01-01",
        "end": "2024-01-31",
    }
    with TestClient(app) as c:
        status = c.get("/yolo/status")
        queued = c.post("/jobs/scene", json=body)
    assert status.json()["available"] is False
    assert str(weights) not in status.text
    assert queued.status_code == 503
    assert "optional dependency" in queued.text


def test_yolo_status_unconfigured(tmp_path: Path) -> None:
    cfg = Settings(
        samples_dir=tmp_path / "samples",
        web_dist=tmp_path / "no-web",
        yolo_weights=None,
    )
    app = create_app(cfg)
    with TestClient(app) as c:
        body = c.get("/yolo/status").json()
    assert body["available"] is False
    assert body["model_id"] is None


def test_scene_job_error_captured(yolo_env: Settings) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> JobResult:
        raise RuntimeError("no scene found")

    app = create_app(yolo_env, scene_runner=_boom)
    with TestClient(app) as c:
        body = {"aoi": {}, "start": "2024-01-01", "end": "2024-01-31"}
        job_id = c.post("/jobs/scene", json=body).json()["job_id"]
        status = c.get(f"/jobs/{job_id}").json()
    assert status["status"] == "error"
    assert "no scene found" in status["detail"]


def test_unknown_job_404(client: TestClient) -> None:
    assert client.get("/jobs/does-not-exist").status_code == 404


# --- app factory ---------------------------------------------------------------


def test_create_app_title(tmp_path: Path) -> None:
    assert create_app(Settings(web_dist=tmp_path / "no-web")).title == "Oil Spill Detection API"


# --- /hindcast -----------------------------------------------------------------


def _hindcast_body() -> dict[str, Any]:
    return {
        "current_oil_slick": {
            "latitude": -20.44,
            "longitude": 57.72,
            "detection_time": "2020-07-25T04:35:00Z",
            "slick_area_km2": 3.1,
        },
        "ocean_currents": [
            {"timestamp": "2020-07-24T04:35:00Z", "eastward_ms": 0.12, "northward_ms": -0.04},
            {"timestamp": "2020-07-25T04:35:00Z", "eastward_ms": 0.09, "northward_ms": -0.02},
        ],
        "winds": [
            {"timestamp": "2020-07-24T04:35:00Z", "eastward_ms": 3.1, "northward_ms": 1.4},
            {"timestamp": "2020-07-25T04:35:00Z", "eastward_ms": 2.8, "northward_ms": 1.1},
        ],
        "config": {"duration_hours": 24, "particle_count": 250},
    }


def test_hindcast_returns_json_and_geojson(client: TestClient) -> None:
    resp = client.post("/hindcast", json=_hindcast_body())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "probable_spill_origin" in body["json"]
    assert body["geojson"]["type"] == "FeatureCollection"
    assert len(body["geojson"]["features"]) > 0


def test_hindcast_rejects_naive_timestamp(client: TestClient) -> None:
    body = _hindcast_body()
    body["current_oil_slick"]["detection_time"] = "2020-07-25T04:35:00"
    resp = client.post("/hindcast", json=body)
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], list)


def test_hindcast_rejects_single_vector(client: TestClient) -> None:
    body = _hindcast_body()
    body["winds"] = body["winds"][:1]
    assert client.post("/hindcast", json=body).status_code == 422


def test_hindcast_rejects_non_positive_area(client: TestClient) -> None:
    body = _hindcast_body()
    body["current_oil_slick"]["slick_area_km2"] = 0
    assert client.post("/hindcast", json=body).status_code == 422
