import type {
  AnalyzeResponse,
  ClusterListResponse,
  ConceptDetail,
  ConceptListResponse,
  FeedbackPayload,
  LectureDetail,
  LectureSummary,
  ModelMetricsResponse,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

/** Static demo build (GitHub Pages): serve a baked snapshot, no backend. */
export const IS_DEMO = import.meta.env.VITE_DEMO === "1";

export class ApiRequestError extends Error {
  code: string;
  status: number;
  detail?: unknown;

  constructor(message: string, code: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.status = status;
    this.detail = detail;
  }
}

const DEMO_DISABLED = new ApiRequestError(
  "This is a static demo. Clone the repo and run it with Docker to upload lectures and give feedback.",
  "demo_read_only",
  403,
);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: init?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
      ...init,
    });
  } catch (err) {
    throw new ApiRequestError(
      "Could not reach the LectureLens API. Is the backend running?",
      "network_error",
      0,
      err,
    );
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!response.ok) {
    const err = data?.error ?? {};
    throw new ApiRequestError(
      err.message ?? `Request failed (${response.status})`,
      err.code ?? "http_error",
      response.status,
      err.detail,
    );
  }
  return data as T;
}

// ---------------------------------------------------------------------------
// Demo-mode backend: a lazily-loaded JSON snapshot of a seeded database.
// ---------------------------------------------------------------------------
interface DemoBundle {
  uploads: LectureSummary[];
  lectures: Record<string, LectureDetail>;
  concepts: Record<string, ConceptListResponse>;
  clusters: Record<string, ClusterListResponse>;
  conceptDetail: Record<string, ConceptDetail>;
  metrics: ModelMetricsResponse;
}

let demoBundle: Promise<DemoBundle> | null = null;
const demo = () => (demoBundle ??= import("../demo/data.json").then((m) => m.default as DemoBundle));

async function demoGet<T>(pick: (b: DemoBundle) => T | undefined, what: string): Promise<T> {
  const value = pick(await demo());
  if (value === undefined) throw new ApiRequestError(`${what} not found`, "not_found", 404);
  return value;
}

export interface UploadArgs {
  courseName: string;
  lectureTitle: string;
  files: File[];
  onProgress?: (percent: number) => void;
}

export function uploadLecture(_: UploadArgs): Promise<{ lecture: LectureDetail; message: string }> {
  if (IS_DEMO) return Promise.reject(DEMO_DISABLED);
  const { courseName, lectureTitle, files, onProgress } = _;
  const form = new FormData();
  form.append("course_name", courseName);
  form.append("lecture_title", lectureTitle);
  files.forEach((file) => form.append("files", file));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE_URL}/uploads`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      const parsed = xhr.responseText ? JSON.parse(xhr.responseText) : undefined;
      if (xhr.status >= 200 && xhr.status < 300) resolve(parsed);
      else {
        const err = parsed?.error ?? {};
        reject(
          new ApiRequestError(
            err.message ?? `Upload failed (${xhr.status})`,
            err.code ?? "upload_error",
            xhr.status,
            err.detail,
          ),
        );
      }
    };
    xhr.onerror = () =>
      reject(new ApiRequestError("Upload failed: network error", "network_error", 0));
    xhr.send(form);
  });
}

export const api = {
  listLectures: () =>
    IS_DEMO ? demoGet((b) => b.uploads, "Lectures") : request<LectureSummary[]>("/uploads"),

  getLecture: (id: number) =>
    IS_DEMO
      ? demoGet((b) => b.lectures[id], `Lecture ${id}`)
      : request<LectureDetail>(`/uploads/${id}`),

  analyzeLecture: (id: number) =>
    IS_DEMO
      ? Promise.reject(DEMO_DISABLED)
      : request<AnalyzeResponse>(`/analyze/${id}`, { method: "POST" }),

  getConcepts: (lectureId: number, params: Record<string, string> = {}) => {
    if (IS_DEMO) return demoGet((b) => b.concepts[lectureId], `Concepts for lecture ${lectureId}`);
    const query = new URLSearchParams(params).toString();
    return request<ConceptListResponse>(
      `/lectures/${lectureId}/concepts${query ? `?${query}` : ""}`,
    );
  },

  getClusters: (lectureId: number) =>
    IS_DEMO
      ? demoGet((b) => b.clusters[lectureId], `Clusters for lecture ${lectureId}`)
      : request<ClusterListResponse>(`/lectures/${lectureId}/clusters`),

  getConcept: (id: number) =>
    IS_DEMO
      ? demoGet((b) => b.conceptDetail[id], `Concept ${id}`)
      : request<ConceptDetail>(`/concepts/${id}`),

  submitFeedback: (conceptId: number, payload: FeedbackPayload) =>
    IS_DEMO
      ? Promise.reject(DEMO_DISABLED)
      : request<unknown>(`/concepts/${conceptId}/feedback`, {
          method: "POST",
          body: JSON.stringify(payload),
        }),

  getModelMetrics: () =>
    IS_DEMO ? demoGet((b) => b.metrics, "Metrics") : request<ModelMetricsResponse>("/models/metrics"),

  health: () =>
    IS_DEMO
      ? Promise.resolve({ status: "demo", version: "static" })
      : request<{ status: string; version: string }>("/health"),
};

export { BASE_URL };
