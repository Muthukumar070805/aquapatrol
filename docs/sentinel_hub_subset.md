# Sentinel Hub Subset API — try later

## Goal

Skip the multi-GB full-scene download in Scene Monitor by fetching only the
AOI as a small processed image via the CDSE **Sentinel Hub process API**
(`sentinel-1-grd`). Status: **researched, not implemented** (verified against
CDSE docs 2026-09-23; no code changes made yet).

## Why this exists

The current Scene Monitor path (`_download_safe_for_aoi`) always downloads the
entire Sentinel-1 product ZIP (1–4 GB) before reading the AOI. On 2026-09-23 a
16673×26016 scene additionally OOM-killed the float64 filter chain
(`lee_filter` holds ~6 full-scene float64 arrays ≈ 19 GiB). The subset API
returns megabytes instead of gigabytes and sidesteps both problems.

## Verified API contract (CDSE docs)

- Endpoint: `POST https://sh.dataspace.copernicus.eu/process/v1`
- Auth: `Authorization: Bearer <token>` where the token comes from the
  **client-credentials grant** with a dashboard OAuth client — i.e. the
  existing `aquapatrol` pair (`CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET`).
  No account password needed. (Ironic but verified: the token that the OData
  *download* endpoint rejects with 401 is exactly the token Sentinel Hub
  expects.)
- Request body keys: `input.bounds.bbox` + `input.bounds.properties.crs`,
  `input.data[]` with `type: "sentinel-1-grd"` and `dataFilter` (`timeRange`,
  `acquisitionMode`, `polarization`, `resolution`, `orbitDirection`,
  `timeliness`), `output.width/height`, `output.responses[].format.type`,
  `evalscript` (JavaScript, `//VERSION=3`).
- Response: binary image (`image/tiff`, `image/png`, …) at the requested size.

## Ready-to-adapt request template (Wakashio genuine case)

```python
request = {
    "input": {
        "bounds": {
            "bbox": [57.58, -20.52, 57.85, -20.32],  # W, S, E, N (Pointe d'Esny)
            "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
        },
        "data": [
            {
                "type": "sentinel-1-grd",
                "dataFilter": {
                    "timeRange": {
                        "from": "2020-08-05T00:00:00Z",
                        "to": "2020-08-15T00:00:00Z",
                    },
                    "acquisitionMode": "IW",
                    "polarization": "DV",
                    "resolution": "HIGH",
                },
            }
        ],
    },
    "output": {
        "width": 2048,
        "height": 2048,
        "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
    },
    "evalscript": "//VERSION=3\n"
    "function setup() { return { input: ['VV'], output: { bands: 1 } }; }\n"
    "function evaluatePixel(s) { return [s.VV]; }",
}

headers = {"Authorization": f"Bearer {token}"}  # client-credentials token
response = requests.post(
    "https://sh.dataspace.copernicus.eu/process/v1",
    headers=headers,
    json=request,
    timeout=120,
)
response.raise_for_status()
open("wakashio_subset.tiff", "wb").write(response.content)
```

## Honest trade-offs (do not skip)

1. **Different pixels.** SH returns processed/orthorectified backscatter, not
   raw SAFE measurement. The YOLO dB-window domain-gap caveat applies in a new
   form — treat first results as experimental and sanity-check against the
   known Wakashio location (SE coast / Blue Bay lagoon).
2. **Quota.** Free-tier processing units are limited: fine for a demo handful
   of requests, not bulk monitoring.
3. **Resolution.** Use `HIGH` to stay near native IW resolution.
4. Rejected alternatives: S3 range-reads (need S3 keys we don't have), COG
   streaming (per-product availability uncertain; code currently deprioritizes
   `_COG`), HTTP Range on the ZIP (cannot spatially subset a measurement TIFF).

## Implementation sketch (when building)

1. New module `src/oilspill/pipeline/sentinel_hub.py`:
   `fetch_s1_subset(bbox, time_range, token, size=2048) -> Path` (GeoTIFF).
   Reuse `get_access_token()` client-credentials flow — no new credentials.
2. Wire as a Scene Monitor option (`source: "full_scene" | "fast_subset"`),
   keeping the full-scene path as fallback. No new dependencies
   (`requests` already in use).
3. Tests: recorded-response tests for request shape + TIFF parsing
   (never hit the live API in tests); live smoke test manually once.
4. Acceptance: Wakashio AOI returns a ≤50 MB TIFF that renders dark
   sea with the slick visible near Pointe d'Esny; YOLO runs on it without OOM.

## References

- CDSE Sentinel Hub `sentinel-1-grd` data + `POST /process/v1` + `client_credentials`
  auth docs (via Context7, 2026-09-23).
- OOM incident: 16673×26016 float64 chain, `src/oilspill/pipeline/preprocess.py`
  `lee_filter` — see AOI-first windowing analysis (companion fix, still open).
- Genuine-case inputs: `docs/case_study/` (AOI `[57.58, -20.52, 57.85, -20.32]`,
  window `2020-08-05 → 2020-08-15`).
