export interface SystemMetrics {
  total_queries: number;
  total_tokens: number;
  avg_latency_ms: number;
  error_rate: number;
  documents_indexed: number;
  uptime_hours: number;
}

export interface QueryMetric {
  timestamp: string;
  query_count: number;
  avg_latency: number;
  error_count: number;
}

export interface DocumentStats {
  total_documents: number;
  total_chunks: number;
  total_embeddings: number;
  last_indexed: string | null;
}
