import { useSamples } from "../hooks/useSamples";
import { sampleSrc } from "../lib/api";
import PipelineDiagram from "../components/PipelineDiagram";

export default function Overview() {
  const samplesQuery = useSamples();
  const samples = samplesQuery.data?.samples ?? [];
  const heroSample = samples.length > 0 ? samples[0] : null;

  return (
    <div>
      <div className="view-head">
        <h1>Overview</h1>
        <p>
          Sentinel-1 SAR oil-spill detection and forensic characterization,
          from raw satellite scenes to vectorized spill polygons.
        </p>
      </div>

      <div className="overview-hero">
        <div className="hero-image">
          {samplesQuery.isLoading && (
            <div style={{ padding: "var(--space-xl)", color: "var(--ink-muted)" }}>
              <span className="spinner" /> Loading sample image...
            </div>
          )}
          {samplesQuery.isError && (
            <div style={{ padding: "var(--space-xl)", color: "var(--danger)" }}>
              Could not load sample images from the API.
            </div>
          )}
          {heroSample && (
            <img
              src={sampleSrc(heroSample.url)}
              alt={`SAR sample: ${heroSample.id}`}
            />
          )}
        </div>

        <div>
          <h3>What YOLO reports</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                className="legend-swatch"
                style={{ background: "#d35400" }}
              />
              <span className="mono">Oil candidate box + confidence</span>
            </div>
            <p className="faint" style={{ fontSize: "0.85rem" }}>
              Every detection is an investigation candidate — not a confirmed
              spill. Use Scene Monitor for full Sentinel-1 scenes and Hindcast
              for drift backtracking.
            </p>
          </div>
        </div>
      </div>

      <div style={{ marginTop: "var(--space-2xl)" }}>
        <h2>Detection pipeline</h2>
        <PipelineDiagram />
      </div>

      <div className="distinction-block">
        <h3>How detection works</h3>

        <p style={{ marginTop: "var(--space-md)" }}>
          <strong>YOLO</strong> is a fast candidate screener. It draws bounding
          boxes around regions that may be oil, producing investigation
          candidates — not confirmed spills. Use it in Quick Detect for single
          images and in Scene Monitor for rapid triage of large Sentinel-1
          areas.
        </p>
      </div>
    </div>
  );
}
