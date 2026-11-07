export type JobStatus = 'queued' | 'running' | 'retrying' | 'completed' | 'failed';
export type JobType = 'inference' | 'rag';
export interface Job {
  id: string;
  prompt: string;
  status: JobStatus;
  result: string | null;
  error: string | null;
  attempts: number;
  created_at?: string;
  finished_at?: string | null;
}
export interface RagResult {
  mode: string;
  answer_status?: "answered" | "insufficient_evidence" | "generation_failed";
  retrieval?: { chunks_found: number; sources: string[]; chunk_ids: string[] };
  answer: string;
  citations: Array<{ source: string; chunk_id: string }>;
  evaluation?: { passed: boolean; metrics: Record<string, number>; failures?: string[] } | null;
  model?: string | null;
  usage?: { input_tokens?: number | null; output_tokens?: number | null } | null;
  performance?: { retrieval_ms: number; generation_ms: number; evaluation_ms: number;
    processing_ms: number; provider_calls: number; repair_attempted: boolean };
}
export function parseRagResult(result: string | null): RagResult | null {
  if (!result) return null;
  try {
    const data: unknown = JSON.parse(result);
    if (!data || typeof data !== 'object') return null;
    const obj = data as Record<string, unknown>;
    if (typeof obj.answer !== 'string' || !Array.isArray(obj.citations)) return null;
    return data as RagResult;
  } catch {
    return null;
  }
}
