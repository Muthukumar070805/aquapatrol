"""YOLO oil-candidate detection orchestration.

This module wires the Sentinel-1 preprocessing chain
(:mod:`oilspill.pipeline.ingest` + :mod:`oilspill.pipeline.preprocess`) to the
YOLO MVP detector (:class:`oilspill.detectors.yolo_detector.YoloDetector`):

* :func:`detect_yolo_from_safe` -- run YOLO on a downloaded SAFE (no network,
  but needs the real product).
* :func:`detect_yolo_from_aoi` -- search the Copernicus Data Space Ecosystem
  for a Sentinel-1 scene over an AOI/date range, download it, then run
  :func:`detect_yolo_from_safe`. This is the only entry point that uses the
  network.
* :func:`_download_safe_for_aoi` -- shared CDSE AOI search/download helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from oilspill.pipeline.preprocess import (
    calibrate_safe,
    land_mask_from_coastlines,
    lee_filter,
    to_db,
)

if TYPE_CHECKING:
    from datetime import datetime

    from oilspill.detectors.contracts import DetectionOutput
    from oilspill.detectors.yolo_detector import YoloDetector
    from oilspill.pipeline.ingest import HttpSession


def detect_yolo_from_safe(
    safe_path: Path | str,
    detector: YoloDetector,
    *,
    polarisation: str = "vv",
    lee_size: int = 7,
    coastlines_path: Path | str | None = None,
    env_context: dict[str, object] | None = None,
) -> DetectionOutput:
    """Run the YOLO MVP on the existing SAFE calibration/preprocessing chain.

    This intentionally stops after filtered dB conversion: YOLO receives the
    detector-specific uint8 rendering inside :class:`YoloDetector`, never a
    segmentation-style normalised tensor.
    """
    scene = calibrate_safe(safe_path, polarisation=polarisation)
    filtered = lee_filter(scene.sigma0, size=lee_size)
    db = to_db(filtered)

    land_mask: np.ndarray | None = None
    if coastlines_path is not None:
        land_mask = land_mask_from_coastlines(
            scene.sigma0.shape,  # type: ignore[arg-type]
            scene.transform,
            scene.crs,
            coastlines_path,
        )
    return detector.detect(
        db,
        scene.transform,
        scene.crs,
        scene_id=Path(safe_path).stem,
        land_mask=land_mask,
        env_context=dict(env_context) if env_context is not None else None,
    )


def _download_safe_for_aoi(
    aoi_path: Path | str,
    start: datetime | str,
    end: datetime | str,
    out_dir: Path | str,
    *,
    download_dir: Path | str | None = None,
    user: str | None = None,
    password: str | None = None,
    polarisation: str = "vv",
    session: HttpSession | None = None,
) -> Path:
    """Reuse the common CDSE AOI search/download flow for YOLO scene jobs."""
    from oilspill.pipeline.ingest import (
        download_product,
        get_access_token,
        load_aoi,
        search_products,
    )

    aoi = load_aoi(aoi_path)
    products = search_products(aoi, start, end, polarisation=polarisation.upper(), session=session)
    if not products:
        raise RuntimeError(f"No Sentinel-1 scenes found for the AOI between {start} and {end}.")
    safe_dir = Path(download_dir) if download_dir is not None else Path(out_dir) / "safe"
    safe_dir.mkdir(parents=True, exist_ok=True)
    from oilspill.pipeline.preprocess import extract_safe_if_zip

    prod_name = products[0].name
    for c_dir in (safe_dir, Path("data/scenes")):
        if not c_dir.exists():
            continue
        target_safe = c_dir / f"{prod_name}.SAFE"
        if not target_safe.exists():
            target_safe = c_dir / prod_name
        if target_safe.is_dir() and (target_safe / "manifest.safe").exists():
            return target_safe

        for zip_cand in (c_dir / f"{prod_name}.SAFE.zip", c_dir / f"{prod_name}.zip"):
            if zip_cand.is_file() and zip_cand.stat().st_size > 10_000_000:
                return extract_safe_if_zip(zip_cand)

    token = get_access_token(user, password, session=session)
    downloaded = download_product(products[0], safe_dir, token, session=session)
    return extract_safe_if_zip(downloaded)


def detect_yolo_from_aoi(
    aoi_path: Path | str,
    start: datetime | str,
    end: datetime | str,
    detector: YoloDetector,
    out_dir: Path | str,
    *,
    download_dir: Path | str | None = None,
    user: str | None = None,
    password: str | None = None,
    polarisation: str = "vv",
    coastlines_path: Path | str | None = None,
    env_context: dict[str, object] | None = None,
    session: HttpSession | None = None,
) -> DetectionOutput:
    """Search/download a Sentinel-1 scene, then run the YOLO pathway."""
    safe_path = _download_safe_for_aoi(
        aoi_path,
        start,
        end,
        out_dir,
        download_dir=download_dir,
        user=user,
        password=password,
        polarisation=polarisation,
        session=session,
    )
    return detect_yolo_from_safe(
        safe_path,
        detector,
        polarisation=polarisation,
        coastlines_path=coastlines_path,
        env_context=env_context,
    )


__all__ = [
    "_download_safe_for_aoi",
    "detect_yolo_from_aoi",
    "detect_yolo_from_safe",
]
