export interface IndexedDocument {
  id: string;
  filename: string;
  upload_date: string;
  chunk_count: number;
  file_size: number;
  status: "indexed" | "processing" | "error";
}

export interface DocumentChunk {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
  similarity_score?: number;
}
