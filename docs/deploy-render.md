# Deploy on Render (Free tier) + GoDaddy domain

Single **Docker** image: FastAPI + React UI. Render sets `PORT`; `scripts/serve.py`
binds `0.0.0.0` and uses that port.

## Free tier — what you get (and what hurts)

| | |
|--|--|
| **Cost** | $0 on [Render Free](https://render.com/docs/free) |
| **RAM** | **512 MB** — tight for PyTorch + YOLO; app may start but **detection can crash** |
| **Sleep** | Service **stops after ~15 minutes** with no traffic |
| **Cold start** | Often **50s–2 min** after sleep before the site responds |
| **Custom domain** | **Supported** on Free web services (GoDaddy DNS still works) |
| **Build time** | Docker build can take several minutes; Free has monthly build/minute limits |

This repo bakes **`best.pt`** into the Docker image and sets smaller YOLO tiles on Render
(`OILSPILL_API_YOLO_TILE_SIZE=640`) to improve odds on 512 MB. After deploy, confirm
`/yolo/status` shows `"available": true` and run Quick Detect on a sample.

If the container **restarts** or **502** only when you click Detect, check Logs for OOM;
you may need a paid instance with more RAM for reliable inference.

**All features on Render:**

| Feature | Needs |
|---------|--------|
| Quick Detect / `/yolo/detect` | Weights in image (default) + `ultralytics` in Docker build |
| Scene Monitor | `CDSE_USER` + `CDSE_PASS` in Render env |
| Cases / vessels / reports | Works; `prototype.db` is ephemeral (resets on redeploy) |

## Prerequisites

- Code on **GitHub** (or GitLab)
- Render account
- GoDaddy domain (optional; you can use `*.onrender.com` only)
- `artifacts/yolo/best.pt` in the repo (baked into the Docker image)

## 1. Create the Free web service

**Blueprint (uses Free plan in `render.yaml`)**

1. [Render dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
2. Connect this repository → approve creation of the `oilspill` web service.
3. Confirm **Instance type: Free** on the service before first deploy.

**Manual**

1. **New** → **Web Service** → connect repo.
2. **Language:** Docker · **Dockerfile:** `./Dockerfile` · root context.
3. **Instance type:** **Free**.
4. **Health check path:** `/healthz`.
5. Do **not** set `PORT` (Render injects it).

## 2. Verify (be patient on Free)

After deploy:

1. Open `https://<service-name>.onrender.com` — if you see “service unavailable”,
   wait 1–2 minutes (cold start).
2. `https://<service-name>.onrender.com/healthz` → `{"status":"ok"}`
3. `https://<service-name>.onrender.com/yolo/status` → ideally `"available": true`
4. `/detect` → try **sample_01** once; if it 502s, check **Logs** for OOM.

**Tip:** Ping `/healthz` after idle to wake the service before showing a demo.

## 3. GoDaddy custom domain (Free tier OK)

1. Render → service → **Settings** → **Custom Domains**.
2. Add `www.yourdomain.com` and `yourdomain.com`.
3. GoDaddy → **DNS**:

| Type | Name | Value |
|------|------|--------|
| CNAME | `www` | `<your-service>.onrender.com` |
| A | `@` | Apex IP(s) from **Render’s** domain instructions |

Use only the records Render shows for your service. TLS is automatic after DNS validates.

## 4. Environment variables

Set in Render → **Environment** only if needed:

| Variable | When |
|----------|------|
| `CDSE_USER` / `CDSE_PASS` | Scene Monitor / CDSE download |
| `OILSPILL_YOLO_HF_REPO` + `HF_TOKEN` | If `best.pt` is **not** in the image |

`render.yaml` already sets `HOST`, weight path, and single-thread hints for Free RAM.

## 5. Redeploy

Push to the linked branch (auto deploy) or **Manual Deploy** → latest commit.

## Local smoke test

```sh
docker compose up --build
```

→ http://localhost:7860
