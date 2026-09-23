import type {
  CaseCreate,
  CaseDetail,
  CaseResponse,
  CorrelationRequest,
  CorrelationResponse,
  HindcastRequest,
  HindcastResponse,
  Job,
  ReportResponse,
  SamplesResponse,
  SceneJobRequest,
  Vessel,
  VesselListResponse,
  VesselTrackPoint,
  YoloImageResponse,
  YoloStatusResponse,
} from "./types";

// Same-origin by default so the app works when served from the API's static
// mount. Override with VITE_API_BASE (e.g. for a separately hosted API).
export const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

function url(path: string): string {
  return `${API_BASE}${path}`;
}

interface ValidationErrorItem {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
}

function formatDetail(detail: unknown, fallback: string): string {
  // FastAPI validation errors arrive as a list of {loc, msg} items; render
  // each as "body -> field: message" instead of "[object Object]".
  if (Array.isArray(detail)) {
    const parts = (detail as ValidationErrorItem[])
      .map((item) => {
        const loc = Array.isArray(item?.loc)
          ? item.loc.filter((p) => p !== "body").join(" → ")
          : "";
        const msg = typeof item?.msg === "string" ? item.msg : "invalid value";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter((part) => part.length > 0);
    if (parts.length > 0) return parts.join("; ");
    return fallback;
  }
  if (typeof detail === "string" && detail.length > 0) return detail;
  return fallback;
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = formatDetail(body?.detail, detail);
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export async function getHealth(): Promise<{ status: string }> {
  return asJson(await fetch(url("/healthz")));
}

export async function getSamples(): Promise<SamplesResponse> {
  return asJson(await fetch(url("/samples")));
}

// Resolve a sample URL against the API base (sample URLs may be root-relative).
export function sampleSrc(sampleUrl: string): string {
  if (/^https?:\/\//.test(sampleUrl)) return sampleUrl;
  return `${API_BASE}${sampleUrl.startsWith("/") ? "" : "/"}${sampleUrl}`;
}

export async function detectYoloImage(
  file: Blob,
  filename = "image.png",
): Promise<YoloImageResponse> {
  const form = new FormData();
  form.append("file", file, filename);
  return asJson(await fetch(url("/yolo/detect"), { method: "POST", body: form }));
}

export async function createSceneJob(
  body: SceneJobRequest,
): Promise<{ job_id: string; status: string }> {
  return asJson(
    await fetch(url("/jobs/scene"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function getJob(id: string): Promise<Job> {
  return asJson(await fetch(url(`/jobs/${id}`)));
}

export async function getYoloStatus(): Promise<YoloStatusResponse> {
  return asJson(await fetch(url("/yolo/status")));
}

export async function runHindcast(body: HindcastRequest): Promise<HindcastResponse> {
  return asJson(
    await fetch(url("/hindcast"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function getVessels(): Promise<VesselListResponse> {
  return asJson(await fetch(url("/vessels")));
}

export async function getVessel(id: string): Promise<Vessel> {
  return asJson(await fetch(url(`/vessels/${id}`)));
}

export async function getVesselTrack(id: string): Promise<VesselTrackPoint[]> {
  return asJson(await fetch(url(`/vessels/${id}/track`)));
}

export async function postCorrelation(body: CorrelationRequest): Promise<CorrelationResponse> {
  return asJson(
    await fetch(url("/correlations"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function createCase(body: CaseCreate): Promise<CaseResponse> {
  return asJson(
    await fetch(url("/cases"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function getCases(): Promise<CaseResponse[]> {
  return asJson(await fetch(url("/cases")));
}

export async function getCase(id: string): Promise<CaseDetail> {
  return asJson(await fetch(url(`/cases/${id}`)));
}

export async function getReport(caseId: string): Promise<ReportResponse> {
  return asJson(await fetch(url(`/reports/${caseId}`)));
}
