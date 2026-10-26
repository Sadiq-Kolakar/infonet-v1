import type {
  AboutResponse,
  DataQualityResponse,
  EntityDetail,
  EntitySummary,
  GraphResponse,
  HealthResponse,
  PageResult,
  SummaryResponse,
} from "./types";

const baseUrl = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: Record<string, unknown>;

  constructor(
    message: string,
    status: number,
    code?: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    const requestSignal = signal
      ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
      : AbortSignal.timeout(15000);
    response = await fetch(`${baseUrl}${path}`, {
      headers: { Accept: "application/json" },
      signal: requestSignal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    if (error instanceof DOMException && error.name === "TimeoutError")
      throw new ApiError("The request took too long. Try again.", 0, "TIMEOUT");
    throw new ApiError(
      "Could not reach the INFONET API. Check that the backend is running.",
      0,
      "NETWORK_ERROR",
    );
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const payload = body as {
      error?: {
        code?: string;
        message?: string;
        details?: Record<string, unknown>;
      };
    } | null;
    throw new ApiError(
      payload?.error?.message ?? `Request failed (${response.status}).`,
      response.status,
      payload?.error?.code,
      payload?.error?.details,
    );
  }
  return body as T;
}

function params(values: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

const relationshipTypes = new Set([
  "AFFILIATED_WITH",
  "HAS_LABORATORY",
  "OFFERS_PROGRAM",
  "IS_HOD_OF",
]);
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function validateGraph(value: unknown): GraphResponse {
  if (
    !isRecord(value) ||
    !Array.isArray(value.nodes) ||
    !Array.isArray(value.edges) ||
    !isRecord(value.meta)
  ) {
    throw new ApiError(
      "The graph endpoint returned an invalid response.",
      502,
      "INVALID_RESPONSE",
    );
  }
  const nodesValid = value.nodes.every(
    (node) =>
      isRecord(node) &&
      isRecord(node.data) &&
      typeof node.data.id === "string" &&
      typeof node.data.label === "string" &&
      typeof node.data.type === "string",
  );
  const edgesValid = value.edges.every(
    (edge) =>
      isRecord(edge) &&
      isRecord(edge.data) &&
      typeof edge.data.id === "string" &&
      typeof edge.data.source === "string" &&
      typeof edge.data.target === "string" &&
      typeof edge.data.type === "string" &&
      relationshipTypes.has(edge.data.type),
  );
  const meta = value.meta;
  const metaValid =
    typeof meta.node_count === "number" &&
    typeof meta.edge_count === "number" &&
    Array.isArray(meta.relationship_types) &&
    meta.relationship_types.every(
      (type) => typeof type === "string" && relationshipTypes.has(type),
    );
  if (!nodesValid || !edgesValid || !metaValid)
    throw new ApiError(
      "The graph endpoint returned an invalid response.",
      502,
      "INVALID_RESPONSE",
    );
  return value as unknown as GraphResponse;
}

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>("/health", signal),
  summary: (signal?: AbortSignal) =>
    request<SummaryResponse>("/summary", signal),
  about: (signal?: AbortSignal) => request<AboutResponse>("/about", signal),
  people: (
    options: {
      q?: string;
      category?: string;
      role_title?: string;
      limit?: number;
      offset?: number;
      order?: "asc" | "desc";
    },
    signal?: AbortSignal,
  ) => request<PageResult<EntitySummary>>(`/people${params(options)}`, signal),
  laboratories: (
    options: { q?: string; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) =>
    request<PageResult<EntitySummary>>(
      `/laboratories${params(options)}`,
      signal,
    ),
  programs: (
    options: { q?: string; level?: string; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) =>
    request<PageResult<EntitySummary>>(`/programs${params(options)}`, signal),
  entity: (id: string, signal?: AbortSignal) =>
    request<EntityDetail>(`/entities/${encodeURIComponent(id)}`, signal),
  graph: async (signal?: AbortSignal) =>
    validateGraph(await request<unknown>("/graph", signal)),
  dataQuality: (signal?: AbortSignal) =>
    request<DataQualityResponse>("/data-quality", signal),
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "DATABASE_UNAVAILABLE")
      return "The INFONET database is currently unavailable. Your request could not be completed.";
    if (error.code === "DATA_NOT_LOADED")
      return "The database is reachable, but no INFONET dataset is loaded.";
    if (error.code === "NOT_FOUND")
      return "This record could not be found in the INFONET dataset.";
    return error.message;
  }
  return "Something went wrong while loading this information.";
}
