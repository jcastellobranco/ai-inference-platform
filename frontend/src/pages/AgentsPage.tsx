import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Table } from '../components/ui';
import { Button, Field, Select, Textarea } from '../components/ui';
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
  'Verifique evidências de confidencialidade, proteção de dados, incidentes e rescisão nos documentos indexados',
  'Analyze this request using the available local tools',
  'Test the ATLAS agent execution pipeline',
];

export function AgentsPage({ token, connected, jobs, refreshJobs, openAccess }: Props) {
  const [question, setQuestion] = useState('');
  const [workflow, setWorkflow] = useState<'tools' | 'research' | 'compliance'>('compliance');
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tokenRef = useRef(token);
  tokenRef.current = token;

  useEffect(() => {
    setQuestion('');
    setWorkflow('compliance');
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
      const created = await jobsApi.createAgent(submittedToken, trimmed, workflow);
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
        <p className="muted">Run a compliance screening against indexed documents, or use research and local MCP tools. Compliance findings are evidence candidates requiring human review. Research can generate a cited answer when an LLM provider is configured; otherwise it displays retrieved evidence.</p>
        <form onSubmit={event => void submit(event)}>
          <Field.Root id="agent-workflow">
            <Field.Label>Execution mode</Field.Label>
            <Select.Control value={workflow}
              onChange={event => setWorkflow(event.target.value as 'tools' | 'research' | 'compliance')}>
              <Select.Option value="compliance">Compliance Auditor · Supplier baseline</Select.Option>
              <Select.Option value="tools">MCP tools · deterministic</Select.Option>
              <Select.Option value="research">Research · LangGraph + RAG + MCP</Select.Option>
            </Select.Control>
          </Field.Root>
          <Field.Root id="agent-question">
            <Field.Label>Task</Field.Label>
            <Textarea rows={6} maxLength={2000} value={question}
              onChange={event => setQuestion(event.target.value)}
              placeholder="Describe a task for the local agent pipeline..." required />
          </Field.Root>
          <Button className="wide-button" type="submit"
            disabled={!connected || submitting || !question.trim()}>
            {submitting ? 'Submitting…' : 'Queue agent workflow ↗'}
          </Button>
        </form>
        {!connected && <p className="inline-hint">To run agents, <Button variant="unstyled" type="button" onClick={openAccess}>connect your JWT →</Button></p>}
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="examples"><span className="eyebrow">EXAMPLE TASKS</span>
          {examples.map(example => <Button variant="unstyled" key={example} type="button" className="example-item"
            onClick={() => setQuestion(example)}><span>{example}</span><span>↗</span></Button>)}
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
            {result.compliance && <section className="answer-panel" aria-label="Compliance screening report">
              <span className="eyebrow">COMPLIANCE SCREENING · {result.compliance.ruleset}</span>
              <h4>Evidence checklist</h4>
              <div className="metric-pills">
                <span>Requirements: <b>{result.compliance.summary.requirements}</b></span>
                <span>Evidence candidates: <b>{result.compliance.summary.evidence_candidates}</b></span>
                <span>Not located: <b>{result.compliance.summary.needs_evidence_review}</b></span>
              </div>
              <p className="muted">{result.compliance.disclaimer}</p>
              {result.compliance.checks.map(check => <details key={check.id} className="evidence-item">
                <summary><strong>{check.requirement}</strong> · {check.status === 'evidence_candidate' ? 'Evidence candidate' : 'Not found in retrieved excerpts'} · Human review required</summary>
                {check.evidence.map((item, index) => <p key={item.chunk_id + index}>
                  <strong>{item.source}</strong> · {item.chunk_id}<span style={{ display: 'block', whiteSpace: 'pre-wrap' }}>{item.excerpt}</span>
                </p>)}
              </details>)}
            </section>}
            {result.research && !result.compliance && <>
              <section className="answer-panel" aria-label="Research answer">
                <span className="eyebrow">RESEARCH ANSWER</span>
                {result.answer_status === 'generated' && result.answer
                  ? <p style={{ whiteSpace: 'pre-wrap' }}>{result.answer}</p>
                  : result.answer_status === 'insufficient_evidence'
                    ? <p>Insufficient evidence to answer this question from the indexed documents.</p>
                    : <p>Answer generation is not enabled. The retrieved excerpts below are evidence, not a synthesized answer.</p>}
                {result.citations && result.citations.length > 0 && <div className="evidence-list">
                  {result.citations.map(citation => <small key={citation.index}>[{citation.index}] {citation.source} · {citation.chunk_id}</small>)}
                </div>}
              </section>
              <details className="eval-box">
                <summary><strong>Retrieved evidence ({result.research.findings.length} chunks)</strong></summary>
                <p className="muted">Research status: {result.research.status}. Excerpts are untrusted source material.</p>
                {result.research.findings.map((finding, index) => <article className="evidence-item" key={index}>
                  <strong>[{index + 1}] {finding.source}</strong>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{finding.observation}</p>
                  <small>{finding.chunk_id ?? 'No chunk ID'}</small>
                </article>)}
              </details>
            </>}
            {!result.research && !result.compliance && <div className="answer-panel">
              <span className="eyebrow">EXECUTION COMPLETE · {result.engine}</span>
              <p>{Object.entries(result.results).map(([id, output]) =>
                `${id}: ${JSON.stringify(output)}`).join('\n')}</p>
            </div>}
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
        <div className="results-note"><span>ⓘ</span><p>Runs are authenticated by ATLAS and stored in its PostgreSQL job queue. Research mode retrieves indexed document evidence using tenant-bound RAG, then runs the bounded MCP tool plan. A cited LLM answer is available only when generation is configured; otherwise inspect the retrieved evidence.</p></div>
      </section>
    </div>
    <section className="panel jobs-panel" style={{ marginTop: 22 }}>
      <div className="panel-topline"><span className="eyebrow">RECENT AGENT RUNS</span>
        <Button variant="unstyled" type="button" className="button-secondary" onClick={() => void refreshJobs()} disabled={!connected}>↻ Refresh</Button></div>
      {agentHistory.length === 0 ? <p className="muted">Completed agent runs will appear here during this session.</p> :
        <Table.Scroll><Table.Root className="jobs-table"><Table.Header><Table.Row>
          <Table.Head scope="col">TASK</Table.Head><Table.Head scope="col">STATUS</Table.Head><Table.Head scope="col">RESULT</Table.Head>
        </Table.Row></Table.Header><Table.Body>{agentHistory.map(job => <Table.Row key={job.id}>
          <Table.Cell className="job-prompt"><strong title={job.prompt}>{job.prompt}</strong><small>{job.id.slice(0, 8)}</small></Table.Cell>
          <Table.Cell><StatusBadge status={job.status}/></Table.Cell>
          <Table.Cell><Button variant="unstyled" type="button" className="button-secondary" onClick={() => setJobId(job.id)}>Inspect ↗</Button></Table.Cell>
        </Table.Row>)}</Table.Body></Table.Root></Table.Scroll>}
    </section>
  </>;
}
