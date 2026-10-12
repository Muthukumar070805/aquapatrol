/**
 * Shared test fixtures and mock data for the AquaPatrol e2e suite.
 */
import type { Page } from "@playwright/test";

// ---------------------------------------------------------------------------
// Canonical image stubs (1x1 transparent PNG – no real backend needed)
// ---------------------------------------------------------------------------
export const PNG_1PX =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC";
export const PNG_DATA_URL = `data:image/png;base64,${PNG_1PX}`;
export const PNG_BYTES = Buffer.from(PNG_1PX, "base64");

// ---------------------------------------------------------------------------
// Shared mock API payloads
// ---------------------------------------------------------------------------
export const HEALTH_OK = { status: "ok" };

export const SAMPLES = {
  samples: [
    { id: "scene-01", url: "/samples/scene-01.png" },
    { id: "scene-02", url: "/samples/scene-02.png" },
  ],
};

export const YOLO_STATUS_OK = {
  available: true,
  model_id: "best.pt",
  detail: "YOLO detector ready (one-class oil candidate model).",
};

export const YOLO_STATUS_UNAVAILABLE = {
  available: false,
  model_id: null,
  detail: "Weights file not found.",
};

export const YOLO_DETECT = {
  model_id: "best.pt",
  width: 1,
  height: 1,
  num_candidates: 2,
  detections: [
    {
      spill_id: "SPILL_001",
      bbox: [0, 0, 1, 1],
      confidence: 0.82,
      class_id: 0,
      class_name: "oil",
      tile_provenance: [0],
    },
    {
      spill_id: "SPILL_002",
      bbox: [10, 10, 50, 50],
      confidence: 0.61,
      class_id: 0,
      class_name: "oil",
      tile_provenance: [1],
    },
  ],
  yolo_result_image: PNG_DATA_URL,
};

export const YOLO_DETECT_EMPTY = {
  model_id: "best.pt",
  width: 1,
  height: 1,
  num_candidates: 0,
  detections: [],
  yolo_result_image: PNG_DATA_URL,
};

export const SCENE_JOB_QUEUED = { job_id: "job-abc123", status: "queued" };

export const JOB_DONE = {
  job_id: "job-abc123",
  status: "done",
  detail: "Completed successfully.",
  result: {
    num_oil_polygons: 1,
    total_oil_area_km2: 0.5,
    yolo_result_image: PNG_DATA_URL,
    geojson: {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: [[[1.8, 40.9], [2.6, 40.9], [2.6, 41.4], [1.8, 41.4], [1.8, 40.9]]],
          },
          properties: {
            spill_id: "SPILL_001",
            confidence: 0.82,
            model_confidence: 0.82,
            class_id: 0,
            class_name: "oil",
            detector_type: "yolo_mvp",
            model_id: "best.pt",
            latitude: 41.15,
            longitude: 2.2,
            bbox: [0, 0, 100, 100],
            tile_provenance: [0],
          },
        },
      ],
    },
  },
};

export const JOB_ERROR = {
  job_id: "job-err999",
  status: "error",
  detail: "Scene processing failed: no valid tiles.",
};

export const HINDCAST_RESPONSE = {
  json: {
    current_oil_slick_location: {
      latitude: -20.44,
      longitude: 57.72,
      slick_area_km2: 3.1,
    },
    detection_time: "2020-07-25T04:35:00Z",
    backward_trajectories: [
      { particle_id: 0, coordinates: [[57.72, -20.44], [57.68, -20.48]] },
      { particle_id: 1, coordinates: [[57.72, -20.44], [57.70, -20.47]] },
    ],
    probable_spill_origin: { latitude: -20.48, longitude: 57.68 },
    estimated_spill_time: "2020-07-24T04:35:00Z",
    origin_probability: 0.87,
  },
  geojson: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [57.72, -20.44] },
        properties: { result: "current_oil_slick" },
      },
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [57.68, -20.48] },
        properties: { result: "probable_spill_origin" },
      },
      {
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: [[57.72, -20.44], [57.68, -20.48]],
        },
        properties: { particle_id: 0 },
      },
    ],
  },
};

export const VESSEL_1 = {
  id: "vessel-001",
  name: "MV Poseidon",
  mmsi: "123456789",
  imo: "IMO1234567",
  flag: "MT",
  vessel_type: "Tanker",
  lat: -20.45,
  lon: 57.71,
  speed: 8.3,
  heading: 275,
  ais_status: "UnderWayUsingEngine",
  dark_vessel: false,
  last_seen: "2020-07-25T04:00:00Z",
  source: "simulated_ais",
};

export const VESSEL_2 = {
  id: "vessel-002",
  name: "MV Dark Star",
  mmsi: "987654321",
  imo: "IMO9876543",
  flag: "PA",
  vessel_type: "Cargo",
  lat: -20.48,
  lon: 57.69,
  speed: 0,
  heading: 0,
  ais_status: "Moored",
  dark_vessel: true,
  last_seen: "2020-07-24T20:00:00Z",
  source: "simulated_ais",
};

export const VESSELS_LIST = { vessels: [VESSEL_1, VESSEL_2], source: "simulated_ais" };

export const VESSEL_TRACK = [
  { timestamp: "2020-07-25T00:00:00Z", lat: -20.40, lon: 57.75, speed: 10.0, heading: 270 },
  { timestamp: "2020-07-25T02:00:00Z", lat: -20.42, lon: 57.73, speed: 9.5, heading: 272 },
  { timestamp: "2020-07-25T04:00:00Z", lat: -20.45, lon: 57.71, speed: 8.3, heading: 275 },
];

export const CORRELATION_RESPONSE = {
  vessel_id: "vessel-001",
  distance_km: 4.2,
  time_difference_hours: 1.5,
  trajectory_match: "HIGH",
  ais_visibility: "PARTIAL",
  dark_vessel_indicator: false,
  correlation_score: 0.78,
  method: "heuristic_v1",
  disclaimer:
    "YOLO hits are investigation candidates — not confirmed spills. This score is a heuristic.",
};

export const CASE_RESPONSE = {
  id: "case-uuid-001",
  case_number: "CASE-2024-001",
  status: "open",
  spill_id: "SPILL_001",
  candidate_confidence: 0.82,
  origin_lat: -20.48,
  origin_lon: 57.68,
  origin_confidence: 0.87,
  risk_level: "HIGH",
  selected_vessel_id: "vessel-001",
  summary: "Suspected tanker discharge near Mauritius EEZ.",
  created_at: "2024-01-15T10:00:00Z",
};

export const CASE_DETAIL = {
  ...CASE_RESPONSE,
  vessel: VESSEL_1,
  correlations: [],
  evidence: [],
  timeline: ["Case opened.", "YOLO detection logged.", "Hindcast complete."],
};

export const REPORT_RESPONSE = {
  case_id: "case-uuid-001",
  case_number: "CASE-2024-001",
  observation_time: "2020-07-25T04:35:00Z",
  spill_candidate: { spill_id: "SPILL_001", confidence: 0.82 },
  estimated_origin: { latitude: -20.48, longitude: 57.68, confidence: 0.87 },
  vessel: VESSEL_1,
  correlation: { score: 0.78, method: "heuristic_v1" },
  evidence: [],
  investigation_signal: { level: "HIGH", score: 0.83, status: "OPEN" },
  disclaimer: "YOLO hits are investigation candidates — not confirmed spills.",
};

// ---------------------------------------------------------------------------
// Route-interception helper: install all common mocks on a Page.
// Individual tests may call page.route() BEFORE this to override specifics.
// ---------------------------------------------------------------------------
export async function mockAllRoutes(page: Page) {
  await page.route("**/healthz", (r) => r.fulfill({ json: HEALTH_OK }));
  await page.route("**/samples", (r) => r.fulfill({ json: SAMPLES }));
  await page.route("**/samples/scene-01.png", (r) =>
    r.fulfill({ contentType: "image/png", body: PNG_BYTES }),
  );
  await page.route("**/samples/scene-02.png", (r) =>
    r.fulfill({ contentType: "image/png", body: PNG_BYTES }),
  );
  await page.route("**/yolo/status", (r) => r.fulfill({ json: YOLO_STATUS_OK }));
  await page.route("**/yolo/detect", (r) => r.fulfill({ json: YOLO_DETECT }));
  await page.route("**/jobs/scene", (r) => r.fulfill({ json: SCENE_JOB_QUEUED }));
  await page.route("**/jobs/job-abc123", (r) => r.fulfill({ json: JOB_DONE }));
  await page.route("**/hindcast", (r) => r.fulfill({ json: HINDCAST_RESPONSE }));
  await page.route("**/vessels", (r) => r.fulfill({ json: VESSELS_LIST }));
  await page.route("**/vessels/vessel-001/track", (r) => r.fulfill({ json: VESSEL_TRACK }));
  await page.route("**/vessels/vessel-001", (r) => r.fulfill({ json: VESSEL_1 }));
  await page.route("**/vessels/vessel-002/track", (r) => r.fulfill({ json: [] }));
  await page.route("**/vessels/vessel-002", (r) => r.fulfill({ json: VESSEL_2 }));
  await page.route("**/correlations", (r) => r.fulfill({ json: CORRELATION_RESPONSE }));
  await page.route("**/cases", (r) => r.fulfill({ json: [CASE_RESPONSE] }));
  await page.route("**/cases/case-uuid-001", (r) => r.fulfill({ json: CASE_DETAIL }));
  await page.route("**/reports/case-uuid-001", (r) => r.fulfill({ json: REPORT_RESPONSE }));
}
