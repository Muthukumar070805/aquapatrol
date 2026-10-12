"""Uvicorn launcher for the oil-spill inference API.

Preferred (repo root, port 7860 for the Vite dev proxy):

    uv run python scripts/serve.py

Or: ``powershell -ExecutionPolicy Bypass -File scripts/start-api.ps1``

Do **not** run ``uvicorn serve:main`` — use ``serve:app`` with ``--port 7860`` if you
need reload::

    uv run uvicorn serve:app --host 0.0.0.0 --port 7860 --reload

(run from ``scripts/`` with that module path, or from repo root with
``oilspill.api.app:create_app --factory`` instead.)

Host and port for ``python scripts/serve.py`` come from ``HOST`` / ``PORT`` (default
``0.0.0.0:7860``).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import uvicorn

from oilspill.api.app import create_app

if TYPE_CHECKING:
    from fastapi import FastAPI

# Built once at import so a single worker reuses the cached ONNX sessions and the
# in-process job store across requests.
app = create_app()


def _server_host_port() -> tuple[str, int]:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "7860"))
    return host, port


def main() -> FastAPI:
    """ASGI app for mistaken ``uvicorn serve:main`` (factory call). Does not start a server."""
    return app


def _run_server() -> None:
    """Start uvicorn (``python scripts/serve.py`` only)."""
    host, port = _server_host_port()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    _run_server()
