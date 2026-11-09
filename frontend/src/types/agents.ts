export interface AgentTraceStep {
  step: string;
  tool: string;
  status: string;
  duration_ms: number;
}

export interface AgentResult {
  engine: 'mcp-planned';
  workflow?: 'tools' | 'research' | 'compliance';
  research?: { status: string; approved: boolean; findings: Array<{ source: string; observation: string; chunk_id?: string | null }> };
  compliance?: { policy?: { document_id: string; source: string }; contracts?: Array<{ document_id: string; source: string; summary: { needs_attention: number; evidence_to_review: number; reference_not_found: number }; checks: Array<{ id: string; requirement: string; status: 'needs_attention' | 'evidence_to_review' | 'reference_not_found'; message: string; review_required: boolean; policy_evidence: Array<{ source: string; document_id: string; chunk_id: string; excerpt: string }>; contract_evidence: Array<{ source: string; document_id: string; chunk_id: string; excerpt: string }> }> }>; ruleset: string; scope: string; disclaimer: string; documents_retrieved: number; chunks_reviewed: number; summary: { requirements?: number; evidence_candidates?: number; needs_evidence_review?: number; contracts?: number; needs_attention?: number; evidence_to_review?: number; reference_not_found?: number }; checks?: Array<{ id: string; requirement: string; status: 'evidence_candidate' | 'not_found_in_retrieval'; review_required: boolean; evidence: Array<{ source: string; chunk_id: string; excerpt: string }> }> };
  answer?: string;
  answer_status?: 'generated' | 'insufficient_evidence' | 'not_configured';
  citations?: Array<{ index: number; source: string; chunk_id: string }>;
  generation?: { model: string; usage?: { input_tokens?: number; output_tokens?: number }; telemetry?: { llm_ms: number; provider_calls: number } };
  status: 'completed' | 'insufficient_evidence';
  planner: 'offline' | 'llm';
  results: Record<string, Record<string, unknown>>;
  trace: AgentTraceStep[];
  tool_calls: number;
  llm_calls: number;
  duration_ms: number;
  run_id: string;
}

export function parseAgentResult(value: string | null): AgentResult | null {
  if (!value) return null;
  try {
    const parsed: unknown = JSON.parse(value);
    if (!parsed || typeof parsed !== 'object') return null;
    const item = parsed as Record<string, unknown>;
    if (item.engine !== 'mcp-planned' || !['completed', 'insufficient_evidence'].includes(String(item.status)) ||
        !item.results || typeof item.results !== 'object' ||
        !Array.isArray(item.trace) || typeof item.duration_ms !== 'number') return null;
    return parsed as AgentResult;
  } catch {
    return null;
  }
}
