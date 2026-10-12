# scripts

Entry-point scripts for the YOLO workflows: scene/SAFE detection (`detect.py`),
serving (`serve.py`), drift backtracking (`hindcast.py`), and coastline
downloads (`download_coastlines.py`). Scripts are thin wrappers around the
`oilspill` package — they parse arguments and call into library code.

## Local dev (Windows)

From the **repo root** (`Oil_spill`), not from `scripts/`:

```powershell
# API + frontend (recommended)
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1

# API only (safe if 7860 is already up)
powershell -ExecutionPolicy Bypass -File scripts/start-api.ps1

# Frontend only (from web/)
npm run dev
```

Backend listens on **7860**; Vite on **5173** proxies `/healthz`, `/yolo`, etc. to 7860.

Do **not** use `uv run uvicorn serve:main` — `serve.py`'s `main()` calls `uvicorn.run()` again and crashes.
Do **not** run `uv run python scripts/serve.py` while your cwd is `scripts/` (looks for `scripts/scripts/serve.py`).
