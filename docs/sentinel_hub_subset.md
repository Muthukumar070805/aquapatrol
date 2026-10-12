# Sentinel Hub Subset API — skipped-download Scene Fetching (try later)

## Goal

Skip the multi-GB full-scene download in Scene Monitor by fetching only the AOI
as a small processed image via the CDSE **Sentinel Hub process API**
(`sentinel-1-grd`).

## Verified API contract (CDSE docs, checked 2026-09-23)

- Endpoint: `POST https://sh.dataspace.copernicus.eu/process/v1`
- Auth: `Authorization: Bearer <OAuth client-credentials token>` — the existing
  `aquapatrol` OAuth client (`CDSE_CLIENT_ID`/`CDSE_CLIENT_SECRET`) is the right
  credential for this endpoint (no account password needed).
- Request selects `input.data[].type = "sentinel-1-grd"` with:
  - `input.bounds.bbox = [W, S, N, E]` + CRS `http://www.opengis.net/def/crs/EPSG/0/4326`
  - `dataFilter.timeRange.from/to` (ISO `Z`)
  - `dataFilter.acquisitionMode = "IW"`, `polarization = "DV"` (VV+VH),
    `resolution = "HIGH"`, `orbitDirection` optional
  - `evalscript` (JavaScript `//VERSION=3`) returning calibrated VV
  - `output.width/height` (e.g. 2048×2048) + `responses[].format.type = "image/tiff"`

## Wakashio reference request (AOI + window from `docs/case_study/`)

```json
{
  "input": {
    "bounds": {
      "bbox": [57.58, -20.52, 57.85, -20.32],
      "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}
    },
    "data": [
      {
        "type": "sentinel-1-grd",
        "dataFilter": {
          "timeRange": {"from": "2020-08-05T00:00:00Z", "to": "2020-08-15T23:59:59Z"},
          "acquisitionMode": "IW",
          "polarization": "DV",
          "resolution": "HIGH"
        }
      }
    ]
  },
  "output": {
    "width": 2048,
    "height": 2048,
    "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]
  },
  "evalscript": "//VERSION=3\nfunction setup() { return { input: [{ bands: [\"VV\"] }], output: { bands: 1, sampleType: SampleType.FLOAT32 } }; }\nfunction evaluatePixel(s) { return [s.VV]; }"
}
```

```sh
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d @sh_request.json https://sh.dataspace.copernicus.eu/process/v1 \
  -o wakashio_subset.tif
```

Get `$ACCESS_TOKEN` via the existing client-credentials flow
(`CDSE_CLIENT_ID`/`CDSE_CLIENT_SECRET` against the CDSE Keycloak token
endpoint); tokens are short-lived (~10–30 min), fetch fresh per request.

## Trade-offs (read before trusting results)

1. **Different pixels**: Sentinel Hub returns processed/orthorectified backscatter,
   not raw SAFE measurement. The YOLO `-25, 0` dB rendering window was bridged
   against raw scenes — treat first subset results as experimental and validate
   location/plausibility against the known Wakashio position before trusting
   counts/areas.
2. **Quota**: free-tier processing units are limited — fine for a demo handful of
   requests, not bulk monitoring.
3. **Coverage**: the API returns the best match in the window (mosaickingOrder);
   confirm the acquisition date in the response before presenting results.
4. Alternatives considered and rejected: S3 range-reads (need S3 keys we don't
   have), HTTP Range on the product ZIP (cannot spatially subset a measurement
   TIFF), COG streaming (availability varies per product; codebase currently
   deprioritizes `_COG` products).

## Implementation sketch (when scheduled)

- New `src/oilspill/pipeline/sentinel_hub.py`: `fetch_s1_subset(aoi, start, end,
  token, *, width=2048, height=2048) -> Path` (GeoTIFF), raising
  `requests.HTTPError` verbatim on non-2xx.
- Wire as a Scene Monitor fetch option ("fast subset" vs "full scene") reusing
  the OAuth token flow; subset GeoTIFF enters the existing
  filter → dB → YOLO chain unchanged.
- Tests with recorded responses only (never live network in suite); no new
  Python dependencies (`requests` already present).
- Acceptance: Wakashio AOI request returns a 2048×2048 VV TIFF in MBs;
  pipeline runs end-to-end on it without the full-scene download or the
  float64 OOM class.

## Status

- [ ] Tried against live API
- [ ] Validated YOLO response on subset imagery
- [ ] Wired into Scene Monitor
