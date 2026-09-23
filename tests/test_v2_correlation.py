"""Tests for the investigative correlation heuristic (SIH Prototype V2, Task M4)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from oilspill.api.app import create_app
from oilspill.api.settings import Settings
from oilspill.forensics.correlation import haversine_km, score_correlation


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        samples_dir=tmp_path / "samples",
        scenes_dir=tmp_path / "scenes",
        web_dist=tmp_path / "no-web",
        prototype_db=tmp_path / "prototype.db",
        yolo_weights=tmp_path / "missing.pt",
    )


def test_coralis_87() -> None:
    """MT CORALIS candidate scores ~87 and is deterministic."""
    origin_lat, origin_lon = -20.44, 57.72
    vessel_lat, vessel_lon = -20.38, 57.66
    distance = haversine_km(origin_lat, origin_lon, vessel_lat, vessel_lon)
    time_diff_h = 2.0833333333  # 02:30Z -> 04:35Z detection.
    first = score_correlation(distance, time_diff_h, "HIGH", "PARTIAL")
    second = score_correlation(distance, time_diff_h, "HIGH", "PARTIAL")
    assert first == second
    assert first["correlation_score"] == second["correlation_score"]
    assert abs(first["correlation_score"] - 87.0) <= 1.5
    assert first["dark_vessel_indicator"] is False
    assert first["trajectory_match"] == "HIGH"
    assert first["ais_visibility"] == "PARTIAL"


def test_weights_boundaries() -> None:
    """Distance/time weights clamp at their bounds; mappings are exact."""
    # Distance: 0km -> 35, 50km -> 0, beyond -> 0.
    assert score_correlation(0.0, 0.0, "HIGH", "FULL")["correlation_score"] == 90.0
    assert score_correlation(50.0, 0.0, "HIGH", "FULL")["correlation_score"] == 55.0
    assert score_correlation(100.0, 0.0, "HIGH", "FULL")["correlation_score"] == 55.0
    # Time: 0h -> 25, 12h -> 0, beyond -> 0.
    assert score_correlation(0.0, 12.0, "HIGH", "FULL")["correlation_score"] == 65.0
    assert score_correlation(0.0, 24.0, "HIGH", "FULL")["correlation_score"] == 65.0
    # Trajectory mapping: HIGH=25, MED=15, LOW=5.
    assert score_correlation(0.0, 0.0, "HIGH", "FULL")["correlation_score"] == 90.0
    assert score_correlation(0.0, 0.0, "MED", "FULL")["correlation_score"] == 80.0
    assert score_correlation(0.0, 0.0, "LOW", "FULL")["correlation_score"] == 70.0
    # AIS mapping: FULL=5, PARTIAL=12, GAP=15.
    assert score_correlation(0.0, 0.0, "HIGH", "GAP")["correlation_score"] == 100.0
    assert score_correlation(0.0, 0.0, "HIGH", "PARTIAL")["correlation_score"] == 97.0
    gap = score_correlation(0.0, 0.0, "HIGH", "GAP")
    assert gap["dark_vessel_indicator"] is True
    full = score_correlation(0.0, 0.0, "HIGH", "FULL")
    assert full["dark_vessel_indicator"] is False


def test_api_post_correlation(tmp_path: Path) -> None:
    """POST /correlations scores the seeded CORALIS candidate."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        # Seed via vessels list, then score.
        assert client.get("/vessels").status_code == 200
        resp = client.post(
            "/correlations",
            json={
                "origin_lat": -20.44,
                "origin_lon": 57.72,
                "vessel_id": "vessel-coralis",
                "trajectory_match": "HIGH",
                "ais_visibility": "PARTIAL",
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vessel_id"] == "vessel-coralis"
    assert body["method"] == "heuristic_v1"
    assert body["disclaimer"] == (
        "Investigative correlation only — candidate vessel, "
        "requires verification. Not proof of responsibility."
    )
    assert abs(body["correlation_score"] - 87.0) <= 1.5
    assert abs(body["time_difference_hours"] - 2.08) <= 0.1
    assert body["dark_vessel_indicator"] is True
    assert body["trajectory_match"] == "HIGH"
    assert body["ais_visibility"] == "PARTIAL"

    # Row persisted to spill_vessel_correlations.
    import sqlite3

    conn = sqlite3.connect(str(tmp_path / "prototype.db"))
    try:
        row = conn.execute(
            "SELECT vessel_id, correlation_score FROM spill_vessel_correlations "
            "WHERE vessel_id = ?",
            ("vessel-coralis",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert abs(row[1] - body["correlation_score"]) < 0.01


def test_api_post_correlation_404(tmp_path: Path) -> None:
    """POST /correlations returns 404 for an unknown vessel."""
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        resp = client.post(
            "/correlations",
            json={
                "origin_lat": -20.44,
                "origin_lon": 57.72,
                "vessel_id": "does-not-exist",
            },
        )
    assert resp.status_code == 404
