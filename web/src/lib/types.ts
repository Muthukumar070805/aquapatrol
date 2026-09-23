// Shapes mirror the backend API contract exactly.
import type { FeatureCollection, Polygon } from "./geojson";

export interface Sample {
  id: string;
  url: string;
}

export interface SamplesResponse {
  samples: Sample[];
}

export type JobStatus = "queued" | "running" | "done" | "error";

export interface JobResult {
  num_oil_polygons: number;
  total_oil_area_km2: number;
  geojson: FeatureCollection;
  yolo_result_image?: string;
}

export interface Job {
  job_id: string;
  status: JobStatus;
  detail?: string;
  result?: JobResult;
}

export interface SceneJobRequest {
  aoi: Polygon;
  start: string;
  end: string;
  detector?: DetectorType;
  environmental_context?: EnvironmentalContext;
}

// --- YOLO types --------------------------------------------------------------

export type DetectorType = "yolo_mvp";

export interface EnvironmentalContext {
  wind_speed_ms?: number;
  optical_corroboration?: boolean;
  optical_conflict?: boolean;
}

export interface YoloImageDetection {
  spill_id: string;
  bbox: [number, number, number, number];
  confidence: number;
  class_id: number;
  class_name: string;
  tile_provenance: number[];
}

export interface YoloImageResponse {
  model_id: string;
  width: number;
  height: number;
  num_candidates: number;
  detections: YoloImageDetection[];
  yolo_result_image: string;
}

export interface YoloRawDetection {
  spill_id: string;
  latitude: number;
  longitude: number;
  bbox: [number, number, number, number];
  confidence: number;
  model_confidence: number;
  class_id: number;
  class_name: string;
  detector_type: DetectorType;
  model_id: string;
  tile_provenance: number[];
}

export interface YoloStatusResponse {
  available: boolean;
  model_id: string | null;
  detail: string;
}

// --- Hindcast types --------------------------------------------------------

export interface HistoricalVector {
  timestamp: string;
  eastward_ms: number;
  northward_ms: number;
}

export interface CurrentOilSlickInput {
  latitude: number;
  longitude: number;
  detection_time: string;
  slick_area_km2: number;
}

export interface HindcastConfigInput {
  duration_hours?: number;
  step_minutes?: number;
  particle_count?: number;
  windage?: number;
  horizontal_diffusivity_m2_s?: number;
  random_seed?: number;
  uncertainty_confidence?: number;
}

export interface HindcastRequest {
  current_oil_slick: CurrentOilSlickInput;
  ocean_currents: HistoricalVector[];
  winds: HistoricalVector[];
  config?: HindcastConfigInput;
}

export interface HindcastResultData {
  current_oil_slick_location: {
    latitude: number;
    longitude: number;
    slick_area_km2: number;
  };
  detection_time: string;
  backward_trajectories: Array<{
    particle_id: number;
    coordinates: [number, number][];
  }>;
  probable_spill_origin: {
    latitude: number;
    longitude: number;
  };
  estimated_spill_time: string;
  origin_probability: number;
}

export interface HindcastResponse {
  json: HindcastResultData;
  geojson: FeatureCollection;
}

// --- Vessel intelligence types ------------------------------------------------

export interface Vessel {
  id: string;
  name: string;
  mmsi: string;
  imo: string;
  flag: string;
  vessel_type: string;
  lat: number;
  lon: number;
  speed: number;
  heading: number;
  ais_status: string;
  dark_vessel: boolean;
  last_seen: string;
  source: "simulated_ais";
}

export interface VesselTrackPoint {
  timestamp: string;
  lat: number;
  lon: number;
  speed: number;
  heading: number;
}

export interface VesselListResponse {
  vessels: Vessel[];
  source: "simulated_ais";
}

export interface CorrelationRequest {
  origin_lat: number;
  origin_lon: number;
  vessel_id: string;
  trajectory_match: "HIGH" | "MED" | "LOW";
  ais_visibility: "FULL" | "PARTIAL" | "GAP";
  case_id?: string | null;
  detection_time?: string | null;
}

export interface CorrelationResponse {
  vessel_id: string;
  distance_km: number;
  time_difference_hours: number;
  trajectory_match: "HIGH" | "MED" | "LOW";
  ais_visibility: "FULL" | "PARTIAL" | "GAP";
  dark_vessel_indicator: boolean;
  correlation_score: number;
  method: "heuristic_v1";
  disclaimer: string;
}

export interface CaseCreate {
  spill_id: string;
  candidate_confidence: number;
  origin_lat: number;
  origin_lon: number;
  origin_confidence: number;
  selected_vessel_id?: string | null;
  summary?: string | null;
}

export interface CaseResponse {
  id: string;
  case_number: string;
  status: string;
  spill_id: string;
  candidate_confidence: number;
  origin_lat: number;
  origin_lon: number;
  origin_confidence: number;
  risk_level: string;
  selected_vessel_id: string | null;
  summary: string | null;
  created_at: string;
}

export interface CaseDetail extends CaseResponse {
  vessel: Vessel | null;
  correlations: Array<Record<string, unknown>>;
  evidence: Array<Record<string, unknown>>;
  timeline: string[];
}

export interface InvestigationSignal {
  level: string;
  score: number;
  status: string;
}

export interface ReportResponse {
  case_id: string;
  case_number: string;
  observation_time: string;
  spill_candidate: Record<string, unknown>;
  estimated_origin: Record<string, unknown>;
  vessel: Vessel | null;
  correlation: Record<string, unknown> | null;
  evidence: Array<Record<string, unknown>>;
  investigation_signal: InvestigationSignal;
  disclaimer: string;
}
