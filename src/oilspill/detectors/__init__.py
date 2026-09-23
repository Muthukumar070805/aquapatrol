"""Detector abstraction layer for oil-spill detection.

Provides the unified output contract and the YOLO MVP bounding-box detector
with image-derived contour extraction, transparent confidence metadata, and
explicit quality flags.
"""

from __future__ import annotations

from oilspill.detectors.contracts import (
    CandidateResult,
    ConfidenceAdjustment,
    DetectionOutput,
    DetectorType,
    GeometryQuality,
    GeometrySource,
)

__all__ = [
    "CandidateResult",
    "ConfidenceAdjustment",
    "DetectionOutput",
    "DetectorType",
    "GeometryQuality",
    "GeometrySource",
]
