import type { GenerateRequest, GenerateResponse, StatusResponse } from "./types";

// Default: the deployed Render backend. Local dev overrides via
// NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 in web/.env.local.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "https://visual-direction-agent-api.onrender.com";

export async function startGeneration(
  request: GenerateRequest
): Promise<GenerateResponse> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with status ${res.status}`);
  }
  return res.json();
}

/** Error carrying the HTTP status so callers can distinguish a vanished
 *  job (404 — backend restarted, in-memory job store wiped) from blips. */
export class ApiError extends Error {
  constructor(message: string, public httpStatus: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function getStatus(jobId: string): Promise<StatusResponse> {
  const res = await fetch(`${API_BASE}/status/${jobId}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail ?? `Request failed with status ${res.status}`,
      res.status
    );
  }
  return res.json();
}

export function moodboardImageUrl(relativeUrl: string): string {
  if (!relativeUrl) return "";
  return `${API_BASE}${relativeUrl}`;
}
