// Thin fetch wrapper for the FastAPI backend (docs/04 §3). Types come from schema.ts, which is
// generated from the backend's OpenAPI: run `pnpm --filter @societyiq/shared api:generate`.
import type { components } from "./schema";

export type Schemas = components["schemas"];

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  /** i18n key from the backend, e.g. "errors.notFound". */
  readonly messageKey: string;
  /** Extra data, e.g. the legal problems behind a refusal. */
  readonly details: unknown;

  constructor(status: number, code: string, messageKey: string, details?: unknown) {
    super(code);
    this.status = status;
    this.code = code;
    this.messageKey = messageKey;
    this.details = details;
  }
}

export interface ApiClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
  patch<T>(path: string, body?: unknown): Promise<T>;
  /** multipart/form-data with one file field named "file". */
  upload<T>(path: string, file: Blob, filename: string): Promise<T>;
  download(path: string): Promise<Blob>;
}

export function createApiClient(baseUrl: string, getToken: () => string | null): ApiClient {
  async function send(method: string, path: string, body?: unknown): Promise<Response> {
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    let payload: BodyInit | undefined;
    if (body instanceof FormData) {
      payload = body; // the browser sets the multipart boundary
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }

    let response: Response;
    try {
      response = await fetch(`${baseUrl}/api/v1${path}`, { method, headers, body: payload });
    } catch {
      throw new ApiError(0, "NETWORK", "errors.network");
    }
    if (!response.ok) await throwFor(response);
    return response;
  }

  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    return (await (await send(method, path, body)).json()) as T;
  }

  return {
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body ?? {}),
    patch: (path, body) => request("PATCH", path, body ?? {}),
    upload: (path, file, filename) => {
      const form = new FormData();
      form.append("file", file, filename);
      return request("POST", path, form);
    },
    download: async (path) => (await send("GET", path)).blob(),
  };
}

async function throwFor(response: Response): Promise<never> {
  const payload = (await response.json().catch(() => null)) as {
    error?: { code?: string; message_key?: string; details?: unknown };
  } | null;
  if (payload?.error?.code) {
    throw new ApiError(
      response.status,
      payload.error.code,
      payload.error.message_key ?? "errors.generic",
      payload.error.details,
    );
  }
  // FastAPI validation errors (422) have another shape; the forms check fields first.
  throw new ApiError(response.status, response.status === 422 ? "INVALID" : "HTTP", "errors.generic");
}
