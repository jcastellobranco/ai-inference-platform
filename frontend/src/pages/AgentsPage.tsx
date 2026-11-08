import { useEffect, useRef, useState, type FormEvent } from 'react';
import { EmptyState } from '../components/EmptyState';
import { SectionHeader } from '../components/SectionHeader';
import { StatusBadge } from '../components/StatusBadge';
import { jobsApi } from '../lib/api';
import { parseAgentResult } from '../types/agents';
import type { Job } from '../types/jobs';

interface Props {
  token: string;
  connected: boolean;
  jobs: Job[];
  refreshJobs: () => Promise<void>;
  openAccess: () => void;
}

const examples = [
  'Count the words in this sentence',
  'Analyze this request using the available local tools',
  'Test the ATLAS agent execution pipeline',
];

export function AgentsPage({ token, connected, jobs, refreshJobs, openAccess }: Props) {
  const [question, setQuestion] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tokenRef = useRef(token);
  tokenRef.current = token;

  useEffect(() => {
    setQuestion('');
    setJobId(null);
    setError(null);
    setSubmitting(false);
  }, [token]);

  const active = jobs.find(job => job.id === jobId);
  const result = parseAgentResult(active?.result ?? null);
  const agentHistory = jobs.filter(job => parseAgentResult(job.result) !== null ||
    (jobId !== null && job.id === jobId));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!connected || submitting || !trimmed || trimmed.length > 2000) return;
    const submittedToken = token;
    setSubmitting(true);
    setError(null);
    try {
      const created = await jobsApi.createAgent(submittedToken, trimmed);
      if (tokenRef.current !== submittedToken) return;
      setJobId(created.id);
      await refreshJobs();
    } catch (failure: unknown) {
      if (tokenRef.current === submittedToken) {
        setError(failure instanceof Error ? failure.message : 'Unable to submit agent job');
      }
    } finally {
      if (tokenRef.current === submittedToken) setSubmitting(false);
    }
  }

  return <>
    <SectionHeader eyebrow="AGENT ORCHESTRATION" title="Multi-Agent workflows"
      description="Submit tenant-bound agent jobs through ATLAS. Monitor the durable queue, MCP tool results and execution trace." />
    <div className="playground-grid">
      <section className="panel query-panel">
        <div className="panel-topline"><span className="eyebrow">WORKFLOW BUILDER</span><span className="step-chip">EXPERIMENTAL</span></div>
        <h3>Run an agent workflow</h3>
        <p className="muted">This first integration uses a deterministic planner and a real MCP word-count tool. It does not yet perform document analysis or LLM reasoning.</p>
        <form onSubmit={event => void submit(event)}>
          <label htmlFor="agent-question">Task</label>
          <textarea id="agent-question" rows={6} maxLength={2000} value={question}
            onChange={event => setQuestion(event.target.value)}
            placeholder="Describe a task for the local agent pipeline..." required />
          <button className="button-primary wide-button" type="submit"
            disabled={!connected || submitting || !question.trim()}>
            {submitting ? 'Submitting…' : 'Queue agent workflow ↗'}
          </button>
        </form>
        {!connected && <p className="inline-hint">To run agents, <button type="button" onClick={openAccess}>connect your JWT →</button></p>}
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="examples"><span className="eyebrow">EXAMPLE TASKS</span>
          {examples.map(example => <button key={example} type="button" className="example-item"
            onClick={() => setQuestion(example)}><span>{example}</span><span>↗</span></button>)}
        </div>
      </section>
      <section className="panel results-panel" aria-live="polite">
        <div className="panel-topline"><span className="eyebrow">EXECUTION</span><span className="count-chip">MCP TRACE</span></div>
        <h3>Results & execution trace</h3>
        {!jobId ? <EmptyState icon="✧" title="No agent execution selected"
          description="Queue a workflow to see its status and MCP tool output." /> : <>
          <div className="result-summary"><span>✧</span><strong>Agent job</strong>{active && <StatusBadge status={active.status} />}</div>
          <code className="job-reference">{jobId}</code>
          {result ? <>
            <div className="answer-panel">
              <span className="eyebrow">EXECUTION COMPLETE · {result.engine}</span>
              <p>{Object.entries(result.results).map(([id, output]) =>
                `${id}: ${JSON.stringify(output)}`).join('\n')}</p>
            </div>
            <section className="eval-box" aria-label="Agent performance">
              <strong>Execution metrics</strong>
              <div className="metric-pills">
                <span>Duration: <b>{result.duration_ms.toFixed(0)} ms</b></span>
                <span>Tools: <b>{result.tool_calls}</b></span>
                <span>LLM calls: <b>{result.llm_calls}</b></span>
                <span>Planner: <b>{result.planner}</b></span>
              </div>
              <p className="muted">Duration is reported by the agent service; it excludes queue wait and frontend polling.</p>
            </section>
            <h4>Tool execution trace</h4>
            <div className="evidence-list">{result.trace.map((step, index) =>
              <article className="evidence-item" key={`${step.step}-${index}`}>
                <div className="evidence-heading"><span className="evidence-number">{String(index + 1).padStart(2, '0')}</span>
                  <strong>{step.step}</strong><span className="evidence-method">{step.status}</span></div>
                <p>{step.tool} · {step.duration_ms.toFixed(1)} ms</p>
              </article>)}</div>
          </> : active?.status === 'failed' ?
            <p className="error-message" role="alert">{active.error || 'Agent execution failed'}</p> :
            <p className="muted">The worker is processing this job. Status refreshes automatically while jobs are active.</p>}
        </>}
        <div className="results-note"><span>ⓘ</span><p>Runs are authenticated by ATLAS and stored in its PostgreSQL job queue. This local demo currently supports one deterministic MCP tool per request.</p></div>
      </section>
    </div>
    <section className="panel jobs-panel" style={{ marginTop: 22 }}>
      <div className="panel-topline"><span className="eyebrow">RECENT AGENT RUNS</span>
        <button type="button" className="button-secondary" onClick={() => void refreshJobs()} disabled={!connected}>↻ Refresh</button></div>
      {agentHistory.length === 0 ? <p className="muted">Completed agent runs will appear here during this session.</p> :
        <div className="table-scroll"><table className="jobs-table"><thead><tr>
          <th scope="col">TASK</th><th scope="col">STATUS</th><th scope="col">RESULT</th>
        </tr></thead><tbody>{agentHistory.map(job => <tr key={job.id}>
          <td className="job-prompt"><strong title={job.prompt}>{job.prompt}</strong><small>{job.id.slice(0, 8)}</small></td>
          <td><StatusBadge status={job.status}/></td>
          <td><button type="button" className="button-secondary" onClick={() => setJobId(job.id)}>Inspect ↗</button></td>
        </tr>)}</tbody></table></div>}
    </section>
  </>;
}
