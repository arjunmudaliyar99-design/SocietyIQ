// Thin fetch wrapper for the FastAPI backend (docs/04 §3). Types come from schema.ts, which is
// generated from the backend's OpenAPI: run `pnpm --filter @societyiq/shared api:generate`.
import type { components } from "./schema";

export type Schemas = components["schemas"];

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  /** i18n key from the backend, e.g. "errors.notFound". */
  readonly messageKey: string;

  constructor(status: number, code: string, messageKey: string) {
    super(code);
    this.status = status;
    this.code = code;
    this.messageKey = messageKey;
  }
}

export interface ApiClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
  patch<T>(path: string, body?: unknown): Promise<T>;
}

export function createApiClient(baseUrl: string, getToken: () => string | null): ApiClient {
  async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";

    let response: Response;
    try {
      response = await fetch(`${baseUrl}/api/v1${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, "NETWORK", "errors.network");
    }
    if (response.ok) return (await response.json()) as T;

    const payload = (await response.json().catch(() => null)) as {
      error?: { code?: string; message_key?: string };
    } | null;
    if (payload?.error?.code) {
      throw new ApiError(response.status, payload.error.code, payload.error.message_key ?? "errors.generic");
    }
    // FastAPI validation errors (422) have another shape; the forms check fields first.
    throw new ApiError(response.status, response.status === 422 ? "INVALID" : "HTTP", "errors.generic");
  }

  return {
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body ?? {}),
    patch: (path, body) => request("PATCH", path, body ?? {}),
  };
}
