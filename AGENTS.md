# AGENTS.md

## Repo layout — read this first

- This repo is the YOLO oil-candidate detection system: Sentinel-1 pipeline → FastAPI + React/MapLibre UI. Run **all** `uv`, `make`, `pytest`, and `docker` commands from the repo root (CI and `compose.yaml` assume that as build context).
- Single detector: Ultralytics YOLO one-class `oil` checkpoint. The old five-class segmentation pipeline was removed; `src/oilspill/models/`, `training/`, `evaluation/`, `packaging/`, `data/` remain only as stub skeletons.
- Canonical serving checkpoint: `artifacts/yolo/best.pt` (tracked in git; the API default — no env setup needed for local runs).

## Commands (all from the repo root)

```sh
uv sync --extra yolo --group dev  # REQUIRED install (API needs ultralytics + opencv at runtime)
make check                        # REQUIRED gate: ruff check + format --check + pyright + pytest -m "not slow" with coverage
make fmt                          # ruff format + ruff check --fix
make test                         # full pytest incl. slow tests
docker compose up                 # serve API + built frontend at http://localhost:7860
```

- Native run: `uv run python scripts/serve.py` (:7860; uses `artifacts/yolo/best.pt` by default, override with `OILSPILL_API_YOLO_WEIGHTS=/abs/path/best.pt`; PowerShell: `$env:OILSPILL_API_YOLO_WEIGHTS="..."`), then `cd web && npm install && npm run dev` (:5173, proxies `/healthz /samples /jobs /yolo /hindcast` → 7860). One server per port — a stale background `serve.py`/`vite` causes bind `10048`; kill it before restarting.
- YOLO scene CLI: `uv run python scripts/detect.py --safe <S1.SAFE> --weights <best.pt> --out outputs/run1` (or `--aoi aoi.geojson --start/--end` for CDSE search+download).
- Hindcast (drift backtrack, no fetching/forecasting): `uv run python scripts/hindcast.py --input <input>.json --output-dir artifacts/hindcast` — see `docs/hindcast.md`.
- Frontend: `npm run build` (`tsc -b && vite build` → `web/dist`, mounted at `/` by the API), `npm run lint` (`eslint --max-warnings 0`), `npm run e2e` (Playwright, backend-free via interception; first run needs `npx playwright install chromium`).
- Frontend toolchain is pinned: vite 5 + maplibre-gl 4. **Never `npm audit fix --force`** — the majors break the `@vitejs/plugin-react@4` peer range and the map API. Use `npm install`, not `npm ci` (lockfile omits platform-specific optional deps needed by the Linux build).

## Conventions that differ from defaults

- **YOLO hits are investigation candidates, never confirmed spills.** `investigation_confidence` is a heuristic, not a probability; contour polygons are tagged `derived_contour`/`approximate` (or `bbox_fallback`).
- API is YOLO-only: `GET /healthz`, `GET /samples*`, `POST /yolo/detect`, `GET /yolo/status`, `POST /jobs/scene` (forced `detector=yolo_mvp`), `GET /jobs/{id}`, `POST /hindcast`. No `/models`, no `/predict`. Missing weights/ultralytics → 503 (never leak the local weights path).
- Detection flows through `oilspill.detectors.yolo_detector` (`sar_to_yolo_image` → `run_tiled_yolo` → global NMS) and `oilspill.api.service` (`detect_yolo_image`, `_run_yolo_detection`, `annotate_yolo_image`). Scene jobs are in-process only (no queue/DB, lost on restart).
- Pytest `slow` marker = large downloads / real-model tests; `make check` skips it. Coverage requires ≥80%. Ruff line-length 100; Pyright `basic` on `src` + `tests`. Pyright flags the lazy `ultralytics` import unless the yolo extra is installed — the suite itself monkeypatches it, so tests pass without weights.
- Pre-commit blocks files >900KB (`check-added-large-files --maxkb=900`) except the intentional `artifacts/yolo/best.pt` serving checkpoint (narrow `exclude` in `.pre-commit-config.yaml`) — never commit datasets or other binaries.

## Gotchas / operational constraints

- Ignored at runtime, never commit: `.env`, `data/*` (except `README.md`, `checksums.sha256`, `samples/`), `artifacts/` (except `yolo/best.pt`), `mlruns/`, `outputs/`, `web/dist`. Template is `.env.example` (`HF_TOKEN`, `CDSE_USER/PASS`, `OILSPILL_API_YOLO_*`).
- `uv lock` cannot be regenerated in restricted environments — do **not** add/remove Python deps without also updating `uv.lock`, or `--locked` installs (CI) break. `onnx`/`onnxruntime` remain installed but unused for this reason.
- Domain-gap control: the YOLO `sar_to_yolo_image()` dB window (`-25, 0`) is an unvalidated bridge between training chips and raw Sentinel-1 scenes — flag any change here as risky.
- Single-image `/yolo/detect` grayscales plain RGB uploads directly; the dB chain applies only to calibrated SAR scenes in the job path. Do not mix the two renderings.
- ONNX references in `Dockerfile`/`compose.yaml`/entrypoint were replaced by YOLO-weights fetching (`OILSPILL_YOLO_HF_REPO`/`OILSPILL_YOLO_HF_FILE` → `OILSPILL_API_YOLO_WEIGHTS`).
- Windows quirks (verified): rasterio picks up PostgreSQL's incompatible `proj.db` — set `PROJ_LIB`/`PROJ_DATA` to `.venv\Lib\site-packages\rasterio\proj_data` or geo tests fail with `CRSError`. A running vite dev server locks `node_modules` native binaries (`esbuild.exe`, rollup `.node`) — kill the `node` process before deleting/reinstalling `node_modules`. If `uv run`/`uv lock` fail with thread errors, invoke `.venv\Scripts\<tool>.exe` directly.
