# syntax=docker/dockerfile:1

# ---- Stage 1: build the web frontend ----
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
# `npm install` (not `npm ci`): the committed lock may have been generated on a
# different OS and omit the host's platform-specific optional deps (e.g. rollup's
# native binary), which breaks the Vite build on linux. install resolves them.
RUN npm install --no-audit --no-fund
COPY web/ ./
RUN npm run build   # -> /web/dist

# ---- Stage 2: python runtime serving the API + static frontend ----
# Official uv image (uv + a system Python 3.11 preinstalled) -- the documented,
# reliable base for uv-managed projects.
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS runtime

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PORT=7860 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better layer caching). The serving set includes
# the YOLO extra (ultralytics + opencv) so the container can run detection.
# torch resolves to the CPU wheel index pinned in pyproject; rasterio/geopandas
# ship manylinux wheels that bundle their native libs, so no system GDAL
# is required.
# LICENSE is required: pyproject sets license = { file = "LICENSE" }, which
# hatchling validates while building the project during uv sync.
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra yolo

# Application code, the built frontend, and the small committed assets the API
# serves: preloaded sample images (/samples).
COPY scripts/ ./scripts/
COPY data/samples/ ./data/samples/
COPY --from=web /web/dist ./web/dist
# Committed serving checkpoint (see .dockerignore exceptions). Omit from private
# forks and use OILSPILL_YOLO_HF_* at startup instead.
COPY artifacts/yolo/best.pt ./artifacts/yolo/best.pt

# If best.pt is not in the build context, the entrypoint can fetch weights from
# the Hugging Face Hub when OILSPILL_YOLO_HF_REPO is set.
# Put the synced virtualenv on PATH and use it directly. We invoke the venv's
# python rather than `uv run` so the container never tries to re-sync (which would
# pull the dev/ml groups) at startup.
ENV PATH="/app/.venv/bin:$PATH" \
    OILSPILL_API_YOLO_WEIGHTS=/app/artifacts/yolo/best.pt \
    OILSPILL_API_WEB_DIST=/app/web/dist
RUN mkdir -p /app/artifacts/yolo

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import os,urllib.request,sys; p=os.environ.get('PORT','7860'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/healthz').status==200 else 1)"

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "scripts/serve.py"]
