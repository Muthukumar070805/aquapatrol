"""Shared pytest fixtures and configuration."""

from __future__ import annotations

import os
import sqlite3
from importlib.util import find_spec
from pathlib import Path

# rasterio/PROJ needs a projection database with layout MINOR >= 6. A
# system-wide PROJ_LIB (e.g. from a PostgreSQL/PostGIS install, MINOR = 2)
# hijacks CRS lookups and fails every geo test with CRSError.
_REQUIRED_PROJ_MINOR = 6


def _proj_db_minor(proj_db: Path) -> int | None:
    """Return DATABASE.LAYOUT.VERSION.MINOR from a PROJ database, if readable."""
    try:
        row = (
            sqlite3.connect(os.fspath(proj_db))
            .execute("SELECT value FROM metadata WHERE key='DATABASE.LAYOUT.VERSION.MINOR'")
            .fetchone()
        )
    except Exception:
        return None
    try:
        return int(row[0]) if row else None
    except (TypeError, ValueError):
        return None


def _ensure_usable_proj_db() -> None:
    """Point PROJ at rasterio's bundled database if the configured one is too old.

    Only overrides when the currently effective database is provably unusable
    (missing, unreadable, or layout MINOR < 6); otherwise the environment is
    left alone so CI keeps using default PROJ discovery. Runs at collection
    time, before any test module imports rasterio.
    """
    saw_unusable = False
    for var in ("PROJ_LIB", "PROJ_DATA"):
        configured = os.environ.get(var)
        if not configured:
            continue
        minor = _proj_db_minor(Path(configured) / "proj.db")
        if minor is not None and minor >= _REQUIRED_PROJ_MINOR:
            return
        saw_unusable = True

    if not saw_unusable:
        return

    spec = find_spec("rasterio")
    if spec is None or not spec.origin:
        return
    bundled = Path(spec.origin).parent / "proj_data" / "proj.db"
    minor = _proj_db_minor(bundled)
    if minor is not None and minor >= _REQUIRED_PROJ_MINOR:
        os.environ["PROJ_LIB"] = str(bundled.parent)
        os.environ["PROJ_DATA"] = str(bundled.parent)


_ensure_usable_proj_db()
