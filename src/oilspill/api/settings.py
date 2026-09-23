"""Runtime configuration for the YOLO inference API.

All paths are resolved here so they can be overridden from the environment (or
a ``.env`` file) without touching code. Every field has a sane default that
works against the repository layout, so the API runs out of the box when
launched from the project root.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_yolo_weights() -> Path | None:
    """First existing checkpoint: local copy, then legacy workspace spots."""
    for candidate in (
        Path("artifacts/yolo/best.pt"),
        Path("../results/weights/best.pt"),
        Path("../results/weights/yolo26n.pt"),
    ):
        if candidate.exists():
            return candidate
    return Path("artifacts/yolo/best.pt")


class Settings(BaseSettings):
    """API settings, overridable via ``OILSPILL_API_*`` environment variables.

    Attributes
    ----------
    samples_dir:
        Directory of preloaded sample SAR images served at ``/samples``.
    scenes_dir:
        Directory where downloaded Sentinel-1 SAFE products are cached.
    web_dist:
        Directory of the built frontend; mounted at ``/`` when it exists.
    coastlines_path:
        Optional Natural Earth land geometry, shared by the scene pathway.
    yolo_*:
        YOLO MVP detector tunables (see ``docs/yolo_mvp.md``).
    """

    model_config = SettingsConfigDict(
        env_prefix="OILSPILL_API_",
        env_file=".env",
        extra="ignore",
    )

    samples_dir: Path = Path("data/samples")
    scenes_dir: Path = Path("data/scenes")
    web_dist: Path = Path("web/dist")

    # SQLite file for the SIH Prototype V2 investigation store. Resolved
    # relative to the CWD (oil-spill-detection/); override with
    # OILSPILL_API_PROTOTYPE_DB for tests or custom locations.
    prototype_db: Path = Path("prototype.db")
    """SQLite file for the SIH Prototype V2 investigation store."""

    # Optional Natural Earth land geometry for land screening.
    coastlines_path: Path | None = None

    # YOLO detector. Canonical checkpoint lives at artifacts/yolo/best.pt
    # (gitignored local copy of the training output); older workspace-root
    # locations are kept as fallbacks. Deployments override via env setting.
    yolo_weights: Path | None = _default_yolo_weights()
    yolo_conf_threshold: float = 0.25
    yolo_iou_threshold: float = 0.45
    yolo_tile_size: int = 1024
    yolo_tile_overlap: int = 128
    yolo_db_min: float = -25.0
    yolo_db_max: float = 0.0
    yolo_contour_min_pixels: int = 50
    yolo_contour_morph_size: int = 3
    yolo_contour_simplify_tolerance: float = 1.0  # metres in projected CRS
    yolo_low_wind_threshold: float = 3.0  # m/s


def get_settings() -> Settings:
    """Return a freshly resolved :class:`Settings` instance."""
    return Settings()


__all__ = ["Settings", "get_settings"]
