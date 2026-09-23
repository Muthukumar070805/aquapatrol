"""Tests for the vessel intelligence API (SIH Prototype V2, Task M3)."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from oilspill.api.app import create_app
from oilspill.api.settings import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        samples_dir=tmp_path / "samples",
        scenes_dir=tmp_path / "scenes",
        web_dist=tmp_path / "no-web",
        prototype_db=tmp_path / "prototype.db",
        yolo_weights=tmp_path / "missing.pt",
    )


def _parse_z(value: str) -> datetime:
    assert value.endswith("Z"), f"timestamp must be ISO Z: {value!r}"
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def test_vessels_list_seeded(tmp_path: Path) -> None:
    """GET /vessels seeds on empty DB and returns 4 vessels."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        resp = client.get("/vessels")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "simulated_ais"
    vessels = body["vessels"]
    assert len(vessels) == 4
    by_id = {v["id"]: v for v in vessels}
    assert by_id["vessel-coralis"]["name"] == "MT CORALIS"
    assert by_id["vessel-coralis"]["dark_vessel"] is True
    assert by_id["vessel-coralis"]["source"] == "simulated_ais"
    # Ordered by id.
    assert [v["id"] for v in vessels] == sorted(v["id"] for v in vessels)


def test_vessel_detail_404(tmp_path: Path) -> None:
    """GET /vessels/{id} returns 404 for unknown ids."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/vessels/does-not-exist").status_code == 404


def test_track_404(tmp_path: Path) -> None:
    """GET /vessels/{id}/track returns 404 for unknown ids."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/vessels/does-not-exist/track").status_code == 404


def test_track_ordered(tmp_path: Path) -> None:
    """GET /vessels/{id}/track returns points ordered by timestamp."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        resp = client.get("/vessels/vessel-coralis/track")
    assert resp.status_code == 200, resp.text
    points = resp.json()
    assert len(points) >= 2
    timestamps = [p["timestamp"] for p in points]
    assert timestamps == sorted(timestamps)
    times = [_parse_z(t) for t in timestamps]
    gaps = [(b - a).total_seconds() / 3600.0 for a, b in itertools.pairwise(times)]
    assert max(gaps) >= 2.0


def _case_payload(**overrides):  # type: ignore[no-untyped-def]
    payload = {
        "spill_id": "spill-001",
        "candidate_confidence": 0.9,
        "origin_lat": -20.44,
        "origin_lon": 57.72,
        "origin_confidence": 0.8,
    }
    payload.update(overrides)
    return payload


def test_create_case_persists(tmp_path: Path) -> None:
    """POST /cases persists and GET /cases/{id} returns the same case."""
    import re

    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        resp = client.post("/cases", json=_case_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert re.match(r"^SIH-2026-\d{3}$", body["case_number"]), body
    assert body["status"] == "open"
    case_id = body["id"]

    with TestClient(app) as client:
        got = client.get(f"/cases/{case_id}")
    assert got.status_code == 200, got.text
    assert got.json()["id"] == case_id
    assert got.json()["case_number"] == body["case_number"]

    with TestClient(app) as client:
        listed = client.get("/cases")
    assert listed.status_code == 200, listed.text
    ids = [c["id"] for c in listed.json()]
    assert case_id in ids


def test_create_case_bad_vessel_400(tmp_path: Path) -> None:
    """POST /cases with an unknown vessel returns 400."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        resp = client.post("/cases", json=_case_payload(selected_vessel_id="does-not-exist"))
    assert resp.status_code == 400, resp.text


def test_case_detail_includes_timeline(tmp_path: Path) -> None:
    """GET /cases/{id} includes a 7-step timeline."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        created = client.post("/cases", json=_case_payload())
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    with TestClient(app) as client:
        resp = client.get(f"/cases/{case_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    timeline = body["timeline"]
    assert len(timeline) == 7
    joined = " ".join(timeline)
    assert "Probable Origin" in joined
    assert "Investigation Case Created" in joined


def test_report_contains_disclaimer(tmp_path: Path) -> None:
    """GET /reports/{id} returns an on-screen report with the exact disclaimer."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        created = client.post("/cases", json=_case_payload())
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    with TestClient(app) as client:
        assert client.get("/reports/does-not-exist").status_code == 404
        resp = client.get(f"/reports/{case_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["case_number"] == created.json()["case_number"]
    assert isinstance(body["observation_time"], str)
    assert isinstance(body["spill_candidate"], dict)
    assert isinstance(body["estimated_origin"], dict)
    assert isinstance(body["evidence"], list)
    signal = body["investigation_signal"]
    assert signal["status"] == "REQUIRES INVESTIGATION"
    assert signal["level"] in {"High", "Medium", "Low"}
    assert body["disclaimer"] == (
        "Simulated demo data — requires verification. "
        "Investigative correlation only, not proof of responsibility."
    )


def test_report_regenerable(tmp_path: Path) -> None:
    """GET /reports/{id} twice returns an identical investigation signal."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        created = client.post("/cases", json=_case_payload())
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    with TestClient(app) as client:
        first = client.get(f"/reports/{case_id}")
        second = client.get(f"/reports/{case_id}")
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["investigation_signal"] == second.json()["investigation_signal"]
    assert first.json() == second.json()
