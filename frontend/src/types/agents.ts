export interface AgentTraceStep {
  step: string;
  tool: string;
  status: string;
  duration_ms: number;
}

export interface AgentResult {
  engine: 'mcp-planned';
  status: 'completed';
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
    if (item.engine !== 'mcp-planned' || item.status !== 'completed' ||
        !item.results || typeof item.results !== 'object' ||
        !Array.isArray(item.trace) || typeof item.duration_ms !== 'number') return null;
    return parsed as AgentResult;
  } catch {
    return null;
  }
}
