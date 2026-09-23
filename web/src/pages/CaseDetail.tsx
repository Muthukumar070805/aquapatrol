import { Link, useParams } from "react-router-dom";
import { useCase, useReport } from "../hooks/useCases";

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asText(value: unknown): string {
  return typeof value === "string" ? value : "—";
}

function aisLabel(row: Record<string, unknown>): string {
  const direct = row["ais_visibility"];
  if (typeof direct === "string" && direct.length > 0) return direct;
  const dark = row["dark_vessel_indicator"];
  if (dark === 1 || dark === true) return "GAP";
  if (dark === 0 || dark === false) return "FULL";
  return "—";
}

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const caseQuery = useCase(id);
  const reportQuery = useReport(id);

  if (!id) {
    return (
      <section>
        <div className="view-head">
          <h1>Investigation Case</h1>
        </div>
        <div className="panel">
          <div className="error-box">Missing case id.</div>
        </div>
      </section>
    );
  }

  if (caseQuery.isLoading) {
    return (
      <section>
        <div className="view-head">
          <h1>Investigation Case</h1>
        </div>
        <div className="panel">
          <p className="muted">Loading case…</p>
        </div>
      </section>
    );
  }

  if (caseQuery.isError || !caseQuery.data) {
    return (
      <section>
        <div className="view-head">
          <h1>Investigation Case</h1>
        </div>
        <div className="panel">
          <div className="error-box">
            {caseQuery.error instanceof Error
              ? caseQuery.error.message
              : "Failed to load case"}
          </div>
          <div className="row" style={{ marginTop: "var(--space-md)" }}>
            <Link to="/vessels">
              <button type="button">Back to vessels</button>
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const detail = caseQuery.data;
  const vessel = detail.vessel;
  const correlations = detail.correlations ?? [];
  const signal = reportQuery.data?.investigation_signal;
  const score = signal ? signal.score : detail.candidate_confidence * 100;
  const level = signal ? signal.level : detail.risk_level;

  const best =
    correlations.length > 0
      ? correlations.reduce((acc, row) => {
          const a = asNumber(acc["correlation_score"]) ?? -1;
          const b = asNumber(row["correlation_score"]) ?? -1;
          return b > a ? row : acc;
        }, correlations[0])
      : null;
  const bestDistance = best ? asNumber(best["distance_km"]) : null;
  const bestTime = best ? asNumber(best["time_difference_hours"]) : null;
  const bestTrajectory =
    best && typeof best["trajectory_match"] === "string"
      ? (best["trajectory_match"] as string).toUpperCase()
      : "";
  const bestAis =
    best && typeof best["ais_visibility"] === "string"
      ? (best["ais_visibility"] as string).toUpperCase()
      : "";
  const bestDark = best
    ? best["dark_vessel_indicator"] === 1 || best["dark_vessel_indicator"] === true
    : false;
  const isNear = bestDistance !== null && bestDistance < 25;
  const isCorridor = bestTrajectory === "HIGH" || bestTrajectory === "MED";
  const isGap = bestDark || bestAis === "GAP" || bestAis === "PARTIAL";
  const isTiming = bestTime !== null && bestTime < 6;

  return (
    <section>
      <div className="view-head">
        <h1>Investigation Case</h1>
        <p>Forensic case file: candidate, origin, vessel, and evidence trail.</p>
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-lg)" }}>
        <h3>
          {detail.case_number} <span className="badge">{detail.status}</span>{" "}
          <span className="badge">{detail.risk_level}</span>
        </h3>
        <div className="stat">
          <span>Case ID</span>
          <span className="val">{detail.id}</span>
        </div>
        {detail.summary && (
          <div className="stat">
            <span>Summary</span>
            <span className="val">{detail.summary}</span>
          </div>
        )}
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-lg)" }}>
        <h3>Candidate</h3>
        <div className="stat">
          <span>Spill ID</span>
          <span className="val">{detail.spill_id}</span>
        </div>
        <div className="stat">
          <span>Confidence</span>
          <span className="val">{detail.candidate_confidence.toFixed(3)}</span>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-lg)" }}>
        <h3>Origin</h3>
        <div className="stat">
          <span>Latitude</span>
          <span className="val">{detail.origin_lat.toFixed(4)}</span>
        </div>
        <div className="stat">
          <span>Longitude</span>
          <span className="val">{detail.origin_lon.toFixed(4)}</span>
        </div>
        <div className="stat">
          <span>Confidence</span>
          <span className="val">{detail.origin_confidence.toFixed(3)}</span>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-lg)" }}>
        <h3>Vessel</h3>
        {vessel ? (
          <div>
            <div className="stat">
              <span>Name</span>
              <span className="val">{vessel.name}</span>
            </div>
            <div className="stat">
              <span>MMSI</span>
              <span className="val">{vessel.mmsi}</span>
            </div>
            <div className="stat">
              <span>IMO</span>
              <span className="val">{vessel.imo}</span>
            </div>
            <div className="stat">
              <span>Type</span>
              <span className="val">{vessel.vessel_type}</span>
            </div>
            <div className="stat">
              <span>Position</span>
              <span className="val">
                {vessel.lat.toFixed(4)}, {vessel.lon.toFixed(4)}
              </span>
            </div>
            <div className="stat">
              <span>AIS status</span>
              <span className="val">{vessel.ais_status}</span>
            </div>
            <div className="stat">
              <span>Dark vessel</span>
              <span className="val">{vessel.dark_vessel ? "yes" : "no"}</span>
            </div>
          </div>
        ) : (
          <p className="muted">No vessel selected for this case.</p>
        )}
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-lg)" }}>
        <h3>Correlation</h3>
        {correlations.length === 0 ? (
          <p className="muted">No correlations recorded for this case.</p>
        ) : (
          <div className="table-wrap">
            <table className="metrics">
              <thead>
                <tr>
                  <th>Distance</th>
                  <th>Time</th>
                  <th>Trajectory</th>
                  <th>AIS</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {correlations.map((row, index) => {
                  const distance = asNumber(row["distance_km"]);
                  const time = asNumber(row["time_difference_hours"]);
                  const scoreValue = asNumber(row["correlation_score"]);
                  return (
                    <tr key={index}>
                      <td>{distance !== null ? `${distance.toFixed(2)} km` : "—"}</td>
                      <td>{time !== null ? `${time.toFixed(2)} h` : "—"}</td>
                      <td>{asText(row["trajectory_match"])}</td>
                      <td>{aisLabel(row)}</td>
                      <td>{scoreValue !== null ? scoreValue.toFixed(1) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-lg)" }}>
        <h3>INVESTIGATION SIGNAL</h3>
        {reportQuery.isLoading ? (
          <p className="muted">Loading signal…</p>
        ) : (
          <div>
            <div className="stat">
              <span>Level</span>
              <span className="val">{level}</span>
            </div>
            {correlations.length === 0 ? (
              <p className="muted">No correlation yet — select a vessel.</p>
            ) : (
              <ul>
                {isNear && <li>✓ Vessel near estimated origin</li>}
                {isCorridor && <li>✓ Track intersects estimated drift corridor</li>}
                {isGap && <li>✓ AIS gap detected</li>}
                {isTiming && <li>✓ Timing is compatible</li>}
              </ul>
            )}
            <div className="stat">
              <span>Correlation score</span>
              <span className="val">Correlation score: {score.toFixed(1)}%</span>
            </div>
            <p className="muted">Heuristic score, not a probability.</p>
            <div className="stat">
              <span>Status</span>
              <span className="val">Status: REQUIRES INVESTIGATION</span>
            </div>
          </div>
        )}
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-lg)" }}>
        <h3>Timeline</h3>
        <ol>
          {detail.timeline.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>

      <div className="row">
        <Link to={`/reports/${detail.id}`}>
          <button type="button" className="primary">
            View report
          </button>
        </Link>
        <Link to="/vessels">
          <button type="button">Back to vessels</button>
        </Link>
      </div>
    </section>
  );
}
