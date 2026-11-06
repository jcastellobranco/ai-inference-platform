export interface KnowledgeDocument {
  document_id: string;
  source: string;
  chunks: number;
  created_at: string;
}

export interface IngestReceipt {
  document_id: string;
  chunks: number;
}

export interface SearchHit {
  chunk_id: string;
  source: string;
  text: string;
  score: number;
  method: string;
}

export interface SearchResponse {
  citations: SearchHit[];
}
