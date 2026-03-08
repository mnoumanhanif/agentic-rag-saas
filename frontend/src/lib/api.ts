// Use relative path so Next.js rewrites in next.config.ts will proxy the request to the backend
const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

// ── Auth helpers ──────────────────────────────────────────────────────────

function getAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  try {
    const stored = localStorage.getItem("rag-auth-store");
    if (stored) {
      const parsed = JSON.parse(stored);
      const token = parsed?.state?.accessToken;
      if (token) return { Authorization: `Bearer ${token}` };
    }
  } catch {
    // ignore
  }
  return {};
}

async function authFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const headers = {
    ...getAuthHeaders(),
    ...(init.headers || {}),
  };
  return fetch(url, { ...init, headers });
}

// ── Types ─────────────────────────────────────────────────────────────────

export interface QueryRequest {
  query: string;
  chat_history: { role: string; content: string }[];
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  query_analysis: Record<string, unknown> | null;
  reflection: Reflection | null;
  steps: string[];
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

export interface HealthResponse {
  status: string;
  version: string;
  llm_available: boolean;
  vector_store_loaded: boolean;
}

export interface UploadResponse {
  message: string;
  files_processed: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  role: string;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  document_count: number;
  total_chunks: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  knowledge_base_id: string | null;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ApiMessage[];
}

export interface ApiMessage {
  id: string;
  role: string;
  content: string;
  sources: Source[] | null;
  query_analysis: Record<string, unknown> | null;
  reflection: Record<string, unknown> | null;
  steps: string[] | null;
  tokens_used: number;
  latency_ms: number;
  created_at: string;
}

export interface SystemMetrics {
  total_users: number;
  active_users: number;
  total_knowledge_bases: number;
  total_documents: number;
  total_conversations: number;
  total_messages: number;
  total_queries_24h: number;
  avg_latency_ms: number;
  total_tokens_used: number;
  error_rate: number;
}

// ── Auth API ──────────────────────────────────────────────────────────────

export async function signup(email: string, password: string, fullName: string = ""): Promise<TokenResponse> {
  const res = await fetch(`${API_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Signup failed" }));
    throw new Error(err.detail || "Signup failed");
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    throw new Error(err.detail || "Invalid credentials");
  }
  return res.json();
}

export async function refreshTokens(refreshToken: string): Promise<TokenResponse> {
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) throw new Error("Token refresh failed");
  return res.json();
}

// ── RAG queries ───────────────────────────────────────────────────────────

export async function queryRAG(request: QueryRequest): Promise<QueryResponse> {
  const res = await authFetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `Query failed with status ${res.status}`);
  }
  return res.json();
}

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const res = await authFetch(`${API_URL}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `Upload failed with status ${res.status}`);
  }
  return res.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Backend unavailable");
  return res.json();
}

// ── Knowledge Base API ────────────────────────────────────────────────────

export async function createKnowledgeBase(name: string, description: string = ""): Promise<KnowledgeBase> {
  const res = await authFetch(`${API_URL}/knowledge-bases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error("Failed to create knowledge base");
  return res.json();
}

export async function listKnowledgeBases(): Promise<{ knowledge_bases: KnowledgeBase[]; total: number }> {
  const res = await authFetch(`${API_URL}/knowledge-bases`);
  if (!res.ok) throw new Error("Failed to list knowledge bases");
  return res.json();
}

export async function deleteKnowledgeBase(kbId: string): Promise<void> {
  const res = await authFetch(`${API_URL}/knowledge-bases/${kbId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete knowledge base");
}

// ── Conversation API ──────────────────────────────────────────────────────

export async function createConversation(title: string = "New Chat"): Promise<ConversationSummary> {
  const res = await authFetch(`${API_URL}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to create conversation");
  return res.json();
}

export async function listConversations(): Promise<{ conversations: ConversationSummary[]; total: number }> {
  const res = await authFetch(`${API_URL}/conversations`);
  if (!res.ok) throw new Error("Failed to list conversations");
  return res.json();
}

export async function getConversation(convId: string): Promise<ConversationDetail> {
  const res = await authFetch(`${API_URL}/conversations/${convId}`);
  if (!res.ok) throw new Error("Failed to get conversation");
  return res.json();
}

export async function deleteConversation(convId: string): Promise<void> {
  const res = await authFetch(`${API_URL}/conversations/${convId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete conversation");
}

// ── Admin API ─────────────────────────────────────────────────────────────

export async function getSystemMetrics(): Promise<SystemMetrics> {
  const res = await authFetch(`${API_URL}/admin/metrics`);
  if (!res.ok) throw new Error("Failed to fetch system metrics");
  return res.json();
}

export async function getQueryAnalytics(days: number = 7) {
  const res = await authFetch(`${API_URL}/analytics/queries?days=${days}`);
  if (!res.ok) throw new Error("Failed to fetch analytics");
  return res.json();
}

