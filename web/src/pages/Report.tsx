import { Link, useParams } from "react-router-dom";
import { useReport } from "../hooks/useCases";

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asText(value: unknown): string {
  if (typeof value === "string" && value.length > 0) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return "—";
}

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const reportQuery = useReport(id);

  if (!id) {
    return (
      <section>
        <div className="view-head">
          <h1>Incident Report</h1>
        </div>
        <div className="panel">
          <div className="error-box">Missing case id.</div>
        </div>
      </section>
    );
  }

  if (reportQuery.isLoading) {
    return (
      <section>
        <div className="view-head">
          <h1>Incident Report</h1>
        </div>
        <div className="panel">
          <p className="muted">Loading report…</p>
        </div>
      </section>
    );
  }

  if (reportQuery.isError || !reportQuery.data) {
    return (
      <section>
        <div className="view-head">
          <h1>Incident Report</h1>
        </div>
        <div className="panel">
          <div className="error-box">
            {reportQuery.error instanceof Error
              ? reportQuery.error.message
              : "Failed to load report"}
          </div>
          <div className="row" style={{ marginTop: "1rem" }}>
            <button type="button" onClick={() => reportQuery.refetch()}>
              Generate Report
            </button>
            <Link to={`/cases/${id}`}>
              <button type="button">Back to case</button>
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const report = reportQuery.data;
  const spillId = asText(report.spill_candidate["spill_id"]);
  const spillConf = asNumber(report.spill_candidate["confidence"]);
  const originLat = asNumber(report.estimated_origin["lat"]);
  const originLon = asNumber(report.estimated_origin["lon"]);
  const originConf = asNumber(report.estimated_origin["confidence"]);
  const vessel = report.vessel;
  const correlation = report.correlation;
  const evidence = report.evidence ?? [];
  const signal = report.investigation_signal;

  const corrDistance = correlation ? asNumber(correlation["distance_km"]) : null;
  const corrTime = correlation ? asNumber(correlation["time_difference_hours"]) : null;
  const corrScore = correlation ? asNumber(correlation["correlation_score"]) : null;
  const corrTrajectory = correlation ? asText(correlation["trajectory_match"]) : "—";
  const corrAis = correlation
    ? asText(
        correlation["ais_visibility"] ?? correlation["dark_vessel_indicator"],
      )
    : "—";

  return (
    <section>
      <div className="view-head">
        <h1>Incident Report</h1>
        <p>Regenerable on-screen incident report for investigation case {report.case_number}.</p>
      </div>

      <div className="panel">
        <h3>Case ID</h3>
        <div className="stat">
          <span>Case ID</span>
          <span className="val">{report.case_id}</span>
        </div>
        <div className="stat">
          <span>Case number</span>
          <span className="val">{report.case_number}</span>
        </div>
      </div>

      <div className="panel">
        <h3>Satellite detection (demo scenario)</h3>
        <div className="stat">
          <span>Observation time</span>
          <span className="val">{report.observation_time}</span>
        </div>
      </div>

      <div className="panel">
        <h3>Spill candidate</h3>
        <div className="stat">
          <span>Spill ID</span>
          <span className="val">{spillId}</span>
        </div>
        <div className="stat">
          <span>Confidence</span>
          <span className="val">
            {spillConf !== null ? spillConf.toFixed(3) : "—"}
          </span>
        </div>
      </div>

      <div className="panel">
        <h3>Estimated origin</h3>
        <div className="stat">
          <span>Latitude</span>
          <span className="val">
            {originLat !== null ? originLat.toFixed(4) : "—"}
          </span>
        </div>
        <div className="stat">
          <span>Longitude</span>
          <span className="val">
            {originLon !== null ? originLon.toFixed(4) : "—"}
          </span>
        </div>
        <div className="stat">
          <span>Confidence</span>
          <span className="val">
            {originConf !== null ? originConf.toFixed(3) : "—"}
          </span>
        </div>
      </div>

      <div className="panel">
        <h3>Vessel info</h3>
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
          </div>
        ) : (
          <p className="muted">No vessel linked to this case.</p>
        )}
      </div>

      <div className="panel">
        <h3>AIS observations</h3>
        {vessel ? (
          <div>
            <div className="stat">
              <span>AIS status</span>
              <span className="val">{vessel.ais_status}</span>
            </div>
            <div className="stat">
              <span>Dark vessel</span>
              <span className="val">{vessel.dark_vessel ? "yes" : "no"}</span>
            </div>
            <div className="stat">
              <span>Last seen</span>
              <span className="val">{vessel.last_seen}</span>
            </div>
            <div className="stat">
              <span>Correlation AIS</span>
              <span className="val">{corrAis}</span>
            </div>
          </div>
        ) : (
          <p className="muted">No AIS observations for this case.</p>
        )}
      </div>

      <div className="panel">
        <h3>Correlation evidence</h3>
        {correlation ? (
          <div>
            <div className="stat">
              <span>Distance</span>
              <span className="val">
                {corrDistance !== null ? `${corrDistance.toFixed(2)} km` : "—"}
              </span>
            </div>
            <div className="stat">
              <span>Time difference</span>
              <span className="val">
                {corrTime !== null ? `${corrTime.toFixed(2)} h` : "—"}
              </span>
            </div>
            <div className="stat">
              <span>Trajectory</span>
              <span className="val">{corrTrajectory}</span>
            </div>
            <div className="stat">
              <span>Score</span>
              <span className="val">
                {corrScore !== null ? corrScore.toFixed(1) : "—"}
              </span>
            </div>
          </div>
        ) : (
          <p className="muted">No correlation recorded for this case.</p>
        )}
        {evidence.length === 0 ? (
          <p className="muted">No evidence items recorded.</p>
        ) : (
          <div className="table-wrap">
            <table className="metrics">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Title</th>
                  <th>Description</th>
                  <th>Confidence</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((row, index) => (
                  <tr key={index}>
                    <td>{asText(row["evidence_type"])}</td>
                    <td>{asText(row["title"])}</td>
                    <td>{asText(row["description"])}</td>
                    <td>
                      {asNumber(row["confidence"]) !== null
                        ? (asNumber(row["confidence"]) as number).toFixed(3)
                        : "—"}
                    </td>
                    <td>{asText(row["source"])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <h3>Environmental context</h3>
        <div className="stat">
          <span>Note</span>
          <span className="val">Operator-supplied, not fetched</span>
        </div>
        <p className="muted">
          Wind and current forcing used for drift backtracking are historical
          operator inputs. No live environmental fetching is performed in this
          demo.
        </p>
      </div>

      <div className="panel">
        <h3>Investigation signal</h3>
        <div className="stat">
          <span>Level</span>
          <span className="val">{signal.level}</span>
        </div>
        <div className="stat">
          <span>Score</span>
          <span className="val">{signal.score.toFixed(1)}%</span>
        </div>
        <div className="stat">
          <span>Status</span>
          <span className="val">{signal.status}</span>
        </div>
      </div>

      <div className="panel">
        <div className="error-box">Simulated demo data — requires verification. Investigative correlation only, not proof of responsibility.</div>
        <div className="row" style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className="primary"
            disabled={reportQuery.isFetching}
            onClick={() => reportQuery.refetch()}
          >
            {reportQuery.isFetching ? "Generating…" : "Generate Report"}
          </button>
          <button type="button" onClick={() => window.print()}>
            Print
          </button>
          <Link to={`/cases/${report.case_id}`}>
            <button type="button">Back to case</button>
          </Link>
        </div>
      </div>
    </section>
  );
}
