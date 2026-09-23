"""Case-correlation chain alignment tests (review fixes)."""

from __future__ import annotations

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


def _case_payload(**overrides):
    payload = {
        "spill_id": "spill-001",
        "candidate_confidence": 0.5,
        "origin_lat": -20.44,
        "origin_lon": 57.72,
        "origin_confidence": 0.5,
    }
    payload.update(overrides)
    return payload


def test_two_cases_dont_leak_scores(tmp_path: Path) -> None:
    """Correlations scoped to case_id; adhoc never leaks into new cases."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/vessels").status_code == 200
        # Adhoc correlation (no case_id) must not leak.
        adhoc = client.post(
            "/correlations",
            json={
                "origin_lat": -20.44,
                "origin_lon": 57.72,
                "vessel_id": "vessel-coralis",
                "trajectory_match": "HIGH",
                "ais_visibility": "PARTIAL",
            },
        )
        assert adhoc.status_code == 200, adhoc.text
        adhoc_score = float(adhoc.json()["correlation_score"])

        case_a = client.post("/cases", json=_case_payload(selected_vessel_id="vessel-coralis"))
        assert case_a.status_code == 201, case_a.text
        id_a = case_a.json()["id"]
        # New case has no correlations; risk comes from candidate only.
        assert case_a.json()["risk_level"] == "Medium"  # 0.5*100=50
        detail_a = client.get(f"/cases/{id_a}")
        assert detail_a.status_code == 200
        assert detail_a.json()["correlations"] == []
        report_a = client.get(f"/reports/{id_a}")
        assert report_a.status_code == 200, report_a.text
        # Must not inherit the adhoc score.
        assert abs(float(report_a.json()["investigation_signal"]["score"]) - 50.0) < 0.01

        # Link a real correlation to case A.
        linked = client.post(
            "/correlations",
            json={
                "origin_lat": -20.44,
                "origin_lon": 57.72,
                "vessel_id": "vessel-coralis",
                "trajectory_match": "HIGH",
                "ais_visibility": "PARTIAL",
                "case_id": id_a,
            },
        )
        assert linked.status_code == 200, linked.text

        case_b = client.post("/cases", json=_case_payload(selected_vessel_id="vessel-coralis"))
        assert case_b.status_code == 201, case_b.text
        id_b = case_b.json()["id"]
        detail_b = client.get(f"/cases/{id_b}")
        assert detail_b.status_code == 200
        assert detail_b.json()["correlations"] == []
        report_b = client.get(f"/reports/{id_b}")
        assert report_b.status_code == 200
        assert abs(float(report_b.json()["investigation_signal"]["score"]) - 50.0) < 0.01

        # Case A now shows its own correlation.
        report_a2 = client.get(f"/reports/{id_a}")
        assert abs(float(report_a2.json()["investigation_signal"]["score"]) - adhoc_score) < 0.01


def test_vessel_case_link_shows_correlation_in_detail(tmp_path: Path) -> None:
    """POST /cases then POST /correlations with case_id surfaces in detail."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/vessels").status_code == 200
        created = client.post("/cases", json=_case_payload(selected_vessel_id="vessel-coralis"))
        assert created.status_code == 201, created.text
        case_id = created.json()["id"]
        corr = client.post(
            "/correlations",
            json={
                "origin_lat": -20.44,
                "origin_lon": 57.72,
                "vessel_id": "vessel-coralis",
                "trajectory_match": "HIGH",
                "ais_visibility": "GAP",
                "case_id": case_id,
            },
        )
        assert corr.status_code == 200, corr.text
        detail = client.get(f"/cases/{case_id}")
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert len(body["correlations"]) == 1
        assert body["correlations"][0]["vessel_id"] == "vessel-coralis"
        assert body["correlations"][0]["case_id"] == case_id


def test_correlation_detection_time_and_observation(tmp_path: Path) -> None:
    """Optional detection_time accepted; report uses demo detection constant."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/vessels").status_code == 200
        resp = client.post(
            "/correlations",
            json={
                "origin_lat": -20.44,
                "origin_lon": 57.72,
                "vessel_id": "vessel-coralis",
                "detection_time": "2020-07-25T04:35:00Z",
            },
        )
        assert resp.status_code == 200, resp.text
        created = client.post("/cases", json=_case_payload())
        assert created.status_code == 201
        report = client.get(f"/reports/{created.json()['id']}")
        assert report.status_code == 200, report.text
        assert report.json()["observation_time"] == "2020-07-25T04:35:00Z"


def test_correlation_bad_case_id_404(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/vessels").status_code == 200
        resp = client.post(
            "/correlations",
            json={
                "origin_lat": -20.44,
                "origin_lon": 57.72,
                "vessel_id": "vessel-coralis",
                "case_id": "does-not-exist",
            },
        )
        assert resp.status_code == 404


def test_frontend_honest_signaling_strings() -> None:
    """Vessels panel disclaimer + Correlate; CaseDetail conditional checklist."""
    repo = Path(__file__).resolve().parents[1]
    vessels = (repo / "web" / "src" / "pages" / "Vessels.tsx").read_text(encoding="utf-8")
    assert "Investigative correlation only — candidate vessel, requires verification." in vessels
    assert "Correlate" in vessels
    detail = (repo / "web" / "src" / "pages" / "CaseDetail.tsx").read_text(encoding="utf-8")
    assert "No correlation yet — select a vessel." in detail
    assert "Correlation score:" in detail
    assert "Heuristic score, not a probability." in detail
    report = (repo / "web" / "src" / "pages" / "Report.tsx").read_text(encoding="utf-8")
    assert "Satellite detection (demo scenario)" in report
