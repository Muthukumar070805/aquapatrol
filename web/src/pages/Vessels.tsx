import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { createCase, postCorrelation } from "../lib/api";
import type { CorrelationResponse, Vessel } from "../lib/types";
import { useVessels, useVesselTrack } from "../hooks/useVessels";

const RASTER_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const DEFAULT_COLOR = "#0B6E8F";
const SELECTED_COLOR = "#B5541A";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function gapHours(timestamps: string[]): number {
  let maxGap = 0;
  for (let i = 1; i < timestamps.length; i += 1) {
    const prev = new Date(timestamps[i - 1]).getTime();
    const curr = new Date(timestamps[i]).getTime();
    if (!Number.isNaN(prev) && !Number.isNaN(curr)) {
      maxGap = Math.max(maxGap, (curr - prev) / 3_600_000);
    }
  }
  return maxGap;
}

export default function Vessels() {
  const mapEl = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<Map<string, maplibregl.Marker>>(new Map());
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const originLatRaw = searchParams.get("origin_lat") ?? "-20.44";
  const originLonRaw = searchParams.get("origin_lon") ?? "57.72";
  const originLat = Number(originLatRaw) || -20.44;
  const originLon = Number(originLonRaw) || 57.72;

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [trajectoryMatch, setTrajectoryMatch] = useState<"HIGH" | "MED" | "LOW">("HIGH");
  const [aisVisibility, setAisVisibility] = useState<"FULL" | "PARTIAL" | "GAP">("PARTIAL");
  const [correlation, setCorrelation] = useState<CorrelationResponse | null>(null);
  const [corrLoading, setCorrLoading] = useState(false);
  const [corrError, setCorrError] = useState<string | null>(null);
  const [caseError, setCaseError] = useState<string | null>(null);
  const [caseLoading, setCaseLoading] = useState(false);

  const vesselsQuery = useVessels();
  const trackQuery = useVesselTrack(selectedId);

  const vessels: Vessel[] = useMemo(
    () => vesselsQuery.data?.vessels ?? [],
    [vesselsQuery.data],
  );
  const selected: Vessel | undefined = vessels.find((v) => v.id === selectedId);
  const track = useMemo(() => trackQuery.data ?? [], [trackQuery.data]);
  const maxGap = track.length > 1 ? gapHours(track.map((p) => p.timestamp)) : 0;
  const showGap = selected?.dark_vessel === true || maxGap > 1.5 || aisVisibility === "GAP";

  useEffect(() => {
    if (!mapEl.current || map.current) return;
    const m = new maplibregl.Map({
      container: mapEl.current,
      style: RASTER_STYLE,
      center: [57.72, -20.44],
      zoom: 8,
      attributionControl: false,
    });
    m.on("load", () => {
      m.addSource("vessel-track", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      m.addLayer({
        id: "vessel-track-line",
        type: "line",
        source: "vessel-track",
        paint: { "line-color": "#0B6E8F", "line-width": 2 },
      });
    });
    map.current = m;
    return () => {
      m.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const markers = markersRef.current;
    markers.forEach((marker) => marker.remove());
    markers.clear();
    vessels.forEach((v) => {
      const marker = new maplibregl.Marker({
        color: v.id === selectedId ? SELECTED_COLOR : DEFAULT_COLOR,
      })
        .setLngLat([v.lon, v.lat])
        .setPopup(
          new maplibregl.Popup({ offset: 25 }).setHTML(
            `<strong>${escapeHtml(v.name)}</strong><br/>MMSI ${escapeHtml(v.mmsi)}<br/>${v.speed.toFixed(1)} kn`,
          ),
        )
        .addTo(m);
      markers.set(v.id, marker);
    });
    return () => {
      markers.forEach((marker) => marker.remove());
      markers.clear();
    };
  }, [vessels, selectedId]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const line = {
      type: "FeatureCollection" as const,
      features:
        track.length > 1
          ? [
              {
                type: "Feature" as const,
                geometry: {
                  type: "LineString" as const,
                  coordinates: track.map((p) => [p.lon, p.lat]),
                },
                properties: {},
              },
            ]
          : [],
    };
    const apply = () => {
      const src = m.getSource("vessel-track") as maplibregl.GeoJSONSource | undefined;
      if (src) {
        src.setData(line as unknown as GeoJSON.FeatureCollection);
        if (track.length > 1) {
          const bounds = track.reduce(
            (b: maplibregl.LngLatBounds, p) => b.extend([p.lon, p.lat]),
            new maplibregl.LngLatBounds([track[0].lon, track[0].lat], [track[0].lon, track[0].lat]),
          );
          m.fitBounds(bounds, { padding: 60 });
        }
      }
    };
    if (!m.isStyleLoaded()) {
      m.once("load", apply);
      return;
    }
    apply();
  }, [track]);

  const updateOrigin = (key: "origin_lat" | "origin_lon", value: string) => {
    const next = new URLSearchParams(searchParams);
    next.set(key, value);
    setSearchParams(next);
  };

  const runCorrelation = async () => {
    if (!selected) return;
    setCorrLoading(true);
    setCorrError(null);
    setCorrelation(null);
    try {
      const result = await postCorrelation({
        origin_lat: originLat,
        origin_lon: originLon,
        vessel_id: selected.id,
        trajectory_match: trajectoryMatch,
        ais_visibility: selected.dark_vessel ? "GAP" : aisVisibility,
      });
      setCorrelation(result);
    } catch (err: unknown) {
      setCorrError(err instanceof Error ? err.message : "Correlation failed");
    } finally {
      setCorrLoading(false);
    }
  };

  const openCase = async () => {
    if (!selected) return;
    setCaseLoading(true);
    setCaseError(null);
    try {
      const created = await createCase({
        spill_id: `vessel-intel-${selected.id}`,
        candidate_confidence: correlation ? correlation.correlation_score / 100 : 0.5,
        origin_lat: originLat,
        origin_lon: originLon,
        origin_confidence: 0.5,
        selected_vessel_id: selected.id,
        summary: `Vessel intelligence case for ${selected.name}`,
      });
      try {
        await postCorrelation({
          origin_lat: originLat,
          origin_lon: originLon,
          vessel_id: selected.id,
          trajectory_match: trajectoryMatch,
          ais_visibility: selected.dark_vessel ? "GAP" : aisVisibility,
          case_id: created.id,
        });
      } catch (err: unknown) {
        setCaseError(
          err instanceof Error ? `Case created, correlation link failed: ${err.message}` : "Case created, correlation link failed",
        );
        navigate(`/cases/${created.id}`);
        return;
      }
      navigate(`/cases/${created.id}`);
    } catch (err: unknown) {
      setCaseError(err instanceof Error ? err.message : "Case creation failed");
    } finally {
      setCaseLoading(false);
    }
  };

  return (
    <section>
      <div className="view-head">
        <h1>Vessel Intelligence</h1>
        <p>
          Simulated-AIS candidate vessels near the estimated spill origin. Select a vessel to
          inspect its track, run an investigative correlation, and open a case.
        </p>
      </div>

      <div className="scene-grid">
        <div className="panel">
          <h3 style={{ marginBottom: "1rem" }}>Spill Origin</h3>
          <div className="row" style={{ marginBottom: "1rem" }}>
            <div className="field">
              <label>Origin lat</label>
              <input
                type="number"
                step="0.0001"
                value={originLatRaw}
                onChange={(e) => updateOrigin("origin_lat", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Origin lon</label>
              <input
                type="number"
                step="0.0001"
                value={originLonRaw}
                onChange={(e) => updateOrigin("origin_lon", e.target.value)}
              />
            </div>
          </div>

          <h3 style={{ marginBottom: "0.75rem" }}>
            Candidate vessels{" "}
            <span className="badge">simulated_ais</span>
          </h3>
          {vesselsQuery.isLoading && <p className="muted">Loading vessels…</p>}
          {vesselsQuery.isError && (
            <div className="error-box">
              {vesselsQuery.error instanceof Error
                ? vesselsQuery.error.message
                : "Failed to load vessels"}
            </div>
          )}
          <div className="job-list" style={{ marginBottom: "1.25rem" }}>
            {vessels.map((v) => (
              <button
                key={v.id}
                type="button"
                className="job-item"
                style={
                  v.id === selectedId
                    ? { borderColor: SELECTED_COLOR, borderWidth: 2 }
                    : undefined
                }
                onClick={() => {
                  setSelectedId(v.id);
                  setCorrelation(null);
                  setCorrError(null);
                }}
              >
                <span className="job-id">{v.name}</span>
                <span className="muted mono">{v.mmsi}</span>
                {v.dark_vessel && <span className="badge">dark</span>}
              </button>
            ))}
          </div>

          {selected && (
            <div>
              <h3>Selected vessel</h3>
              <div className="stat">
                <span>Name</span>
                <span className="val">{selected.name}</span>
              </div>
              <div className="stat">
                <span>MMSI</span>
                <span className="val">{selected.mmsi}</span>
              </div>
              <div className="stat">
                <span>IMO</span>
                <span className="val">{selected.imo}</span>
              </div>
              <div className="stat">
                <span>Type</span>
                <span className="val">{selected.vessel_type}</span>
              </div>
              <div className="stat">
                <span>Position</span>
                <span className="val">
                  {selected.lat.toFixed(4)}, {selected.lon.toFixed(4)}
                </span>
              </div>
              <div className="stat">
                <span>Speed</span>
                <span className="val">{selected.speed.toFixed(1)} kn</span>
              </div>
              <div className="stat">
                <span>Heading</span>
                <span className="val">{selected.heading.toFixed(0)}°</span>
              </div>
              <div className="stat">
                <span>AIS status</span>
                <span className="val">{selected.ais_status}</span>
              </div>
              <div className="stat">
                <span>Last seen</span>
                <span className="val" style={{ fontSize: "0.85rem" }}>
                  {selected.last_seen}
                </span>
              </div>
              <div className="stat">
                <span>Dark vessel</span>
                <span className="val">{selected.dark_vessel ? "yes" : "no"}</span>
              </div>
              {trackQuery.isLoading && <p className="muted">Loading track…</p>}
              {showGap && (
                <p style={{ marginTop: "0.75rem" }}>
                  <span className="badge">AIS GAP</span>
                </p>
              )}

              <div className="row" style={{ marginTop: "1rem", marginBottom: "0.75rem" }}>
                <div className="field">
                  <label>Trajectory</label>
                  <select
                    value={trajectoryMatch}
                    onChange={(e) =>
                      setTrajectoryMatch(e.target.value as "HIGH" | "MED" | "LOW")
                    }
                  >
                    <option value="HIGH">HIGH</option>
                    <option value="MED">MED</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
                <div className="field">
                  <label>AIS visibility</label>
                  <select
                    value={aisVisibility}
                    onChange={(e) =>
                      setAisVisibility(e.target.value as "FULL" | "PARTIAL" | "GAP")
                    }
                  >
                    <option value="FULL">FULL</option>
                    <option value="PARTIAL">PARTIAL</option>
                    <option value="GAP">GAP</option>
                  </select>
                </div>
              </div>

              <button
                type="button"
                className="primary"
                style={{ width: "100%" }}
                disabled={corrLoading}
                onClick={runCorrelation}
              >
                {corrLoading ? "Correlating…" : "Correlate"}
              </button>
              {corrError && (
                <div className="error-box" style={{ marginTop: "0.75rem" }}>
                  {corrError}
                </div>
              )}

              {correlation && (
                <div style={{ marginTop: "1rem" }}>
                  <h3>Investigative correlation</h3>
                  <p className="muted">
                    Investigative correlation only — candidate vessel, requires verification.
                  </p>
                  <div className="stat">
                    <span>Distance</span>
                    <span className="val">{correlation.distance_km.toFixed(2)} km</span>
                  </div>
                  <div className="stat">
                    <span>Time difference</span>
                    <span className="val">
                      {correlation.time_difference_hours.toFixed(2)} h
                    </span>
                  </div>
                  <div className="stat">
                    <span>Trajectory</span>
                    <span className="val">{correlation.trajectory_match}</span>
                  </div>
                  <div className="stat">
                    <span>AIS</span>
                    <span className="val">{correlation.ais_visibility}</span>
                  </div>
                  <div className="stat">
                    <span>Score</span>
                    <span className="val">{correlation.correlation_score.toFixed(1)}</span>
                  </div>
                  <button
                    type="button"
                    style={{ width: "100%", marginTop: "0.75rem" }}
                    disabled={caseLoading}
                    onClick={openCase}
                  >
                    {caseLoading ? "Creating case…" : "Create Case"}
                  </button>
                  {caseError && (
                    <div className="error-box" style={{ marginTop: "0.75rem" }}>
                      {caseError}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <div ref={mapEl} className="map" />
      </div>
    </section>
  );
}
