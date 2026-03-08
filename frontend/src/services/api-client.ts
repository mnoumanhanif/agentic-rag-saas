/**
 * Centralized API client for all backend communication.
 * All requests go through Next.js API routes which proxy to the backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || `Request failed: ${res.status}`);
  }

  return res.json();
}

// ── Chat & Query ────────────────────────────────────────────

export interface QueryRequest {
  query: string;
  chat_history: { role: string; content: string }[];
}

export interface Source {
  content: string;
  metadata: Record<string, unknown>;
}

export interface Reflection {
  score: number;
  is_faithful: boolean;
  has_hallucination: boolean;
  feedback: string;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  query_analysis: Record<string, unknown> | null;
  reflection: Reflection | null;
  steps: string[];
}

export function queryRAG(req: QueryRequest): Promise<QueryResponse> {
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// ── File Upload ─────────────────────────────────────────────

export interface UploadResponse {
  message: string;
  files_processed: string[];
}

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || `Upload failed: ${res.status}`);
  }

  return res.json();
}

// ── Health ──────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  llm_available: boolean;
  vector_store_loaded: boolean;
}

// Bypass cache for health checks to always get fresh system status
export function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { cache: "no-store" });
}

export { ApiError };
