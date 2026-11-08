export interface AgentTraceStep {
  step: string;
  tool: string;
  status: string;
  duration_ms: number;
}

export interface AgentResult {
  engine: 'mcp-planned';
  workflow?: 'tools' | 'research';
  research?: { status: string; approved: boolean; findings: Array<{ source: string; observation: string; chunk_id?: string | null }> };
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
