"""Investigative vessel-correlation heuristic (heuristic_v1).

Scores how closely a candidate vessel aligns with a slick origin in
distance, time, trajectory, and AIS visibility. Outputs are investigative
candidates only — they require verification and are never attribution.
"""

from __future__ import annotations

import math

_EARTH_RADIUS_KM = 6371.0
_MAX_DISTANCE_KM = 50.0
_MAX_TIME_H = 12.0

_TRAJECTORY_SCORES = {"HIGH": 25.0, "MED": 15.0, "LOW": 5.0}
_AIS_SCORES = {"FULL": 5.0, "PARTIAL": 12.0, "GAP": 15.0}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two WGS84 points."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def classify_trajectory(heading_diff_deg: float) -> str:
    """Map a heading difference to HIGH/MED/LOW (investigative helper)."""
    diff = abs(heading_diff_deg) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    if diff <= 30.0:
        return "HIGH"
    if diff <= 90.0:
        return "MED"
    return "LOW"


def score_correlation(
    distance_km: float,
    time_diff_h: float,
    trajectory_match: str,
    ais_visibility: str,
) -> dict:
    """Score a candidate vessel against a slick origin.

    Weights: distance 35 (0km=35, linear to 0 at 50km), time 25
    (0h=25, 0 at 12h), trajectory 25 (HIGH=25, MED=15, LOW=5),
    AIS 15 (FULL=5, PARTIAL=12, GAP=15). Inputs beyond the distance
    or time bounds clamp to zero for that component.
    """
    traj_key = str(trajectory_match).strip().upper()
    ais_key = str(ais_visibility).strip().upper()
    if traj_key not in _TRAJECTORY_SCORES:
        raise ValueError(f"Unknown trajectory_match: {trajectory_match!r}")
    if ais_key not in _AIS_SCORES:
        raise ValueError(f"Unknown ais_visibility: {ais_visibility!r}")

    dist = max(0.0, float(distance_km))
    hours = max(0.0, abs(float(time_diff_h)))
    distance_score = 35.0 * max(0.0, 1.0 - dist / _MAX_DISTANCE_KM)
    time_score = 25.0 * max(0.0, 1.0 - hours / _MAX_TIME_H)
    trajectory_score = _TRAJECTORY_SCORES[traj_key]
    ais_score = _AIS_SCORES[ais_key]
    total = round(distance_score + time_score + trajectory_score + ais_score, 1)
    return {
        "distance_km": float(distance_km),
        "time_difference_hours": float(time_diff_h),
        "trajectory_match": traj_key,
        "ais_visibility": ais_key,
        "dark_vessel_indicator": ais_key == "GAP",
        "correlation_score": total,
    }


__all__ = ["classify_trajectory", "haversine_km", "score_correlation"]
