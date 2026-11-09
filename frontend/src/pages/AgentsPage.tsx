import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Table } from '../components/ui';
import { Button, Field, Input, Select, Textarea } from '../components/ui';
import { EmptyState } from '../components/EmptyState';
import { SectionHeader } from '../components/SectionHeader';
import { StatusBadge } from '../components/StatusBadge';
import { jobsApi } from '../lib/api';
import { knowledgeApi } from '../lib/knowledgeApi';
import type { KnowledgeDocument } from '../types/knowledge';
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
  'Check whether the contracts include incident notification clauses.',
  'Identify potential gaps in personal data protection clauses.',
  'Review confidentiality and termination requirements.',
];
const DEFAULT_AUDIT_TASK = 'Compare selected contracts against the reference policy using the four baseline requirements.';

export function AgentsPage({ token, connected, jobs, refreshJobs, openAccess }: Props) {
  const [question, setQuestion] = useState('');
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [policyId, setPolicyId] = useState('');
  const [targetIds, setTargetIds] = useState<string[]>([]);
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [loadingLibrary, setLoadingLibrary] = useState(false);
  const [workflow, setWorkflow] = useState<'tools' | 'research' | 'compliance'>('compliance');
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLElement | null>(null);
  const tokenRef = useRef(token);
  tokenRef.current = token;

  useEffect(() => {
    setQuestion('');
    setDocuments([]);
    setPolicyId('');
    setTargetIds([]);
    setLibraryError(null);
    setWorkflow('compliance');
    setJobId(null);
    setError(null);
    setSubmitting(false);
  }, [token]);

  useEffect(() => {
    if (!connected || !token) return;
    let cancelled = false;
    setLoadingLibrary(true);
    void knowledgeApi.list(token).then(data => {
      if (!cancelled) {
        setDocuments(data.items);
        setPolicyId(current => data.items.some(item => item.document_id === current) ? current : '');
        setTargetIds(current => current.filter(id => data.items.some(item => item.document_id === id)));
      }
    }).catch(() => {
      if (!cancelled) setLibraryError('Unable to load indexed documents.');
    }).finally(() => {
      if (!cancelled) setLoadingLibrary(false);
    });
    return () => { cancelled = true; };
  }, [connected, token]);

  const canAudit = Boolean(policyId && targetIds.length > 0 && targetIds.length <= 4 &&
    !targetIds.includes(policyId) && !loadingLibrary && !libraryError);
  const active = jobs.find(job => job.id === jobId);
  const result = parseAgentResult(active?.result ?? null);
  function inspect(id: string) {
    setJobId(id);
    resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const agentHistory = jobs.filter(job => parseAgentResult(job.result) !== null ||
    (jobId !== null && job.id === jobId));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim() || (workflow === 'compliance' ? DEFAULT_AUDIT_TASK : '');
    if (!connected || submitting || !trimmed || trimmed.length > 2000 || (workflow === 'compliance' && !canAudit)) return;
    const submittedToken = token;
    setSubmitting(true);
    setError(null);
    try {
      const created = await jobsApi.createAgent(submittedToken, trimmed, workflow,
        workflow === 'compliance' ? { policy_document_id: policyId, target_document_ids: targetIds } : undefined);
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
    <SectionHeader eyebrow="INTELLIGENT DOCUMENT REVIEW" title="AI Compliance Auditor"
      description="Screen indexed documents for contractual safeguards and review source-backed findings. Human validation is required." />
    <div className="playground-grid">
      <section className="panel query-panel">
        <div className="panel-topline"><span className="eyebrow">NEW AUDIT</span><span className="step-chip">EARLY ACCESS</span></div>
        <h3>New contract review</h3>
        <p className="muted">Compare your contracts against a corporate policy and identify items that need attention before approval.</p>
        <form onSubmit={event => void submit(event)}>
          {workflow === 'compliance' && <>
            <div className="audit-step">
              <h4>1. Select your reference policy</h4>
              <p className="muted">Choose the document that defines the requirements to check.</p>
              <Field.Root id="audit-policy">
                <Field.Label>Reference policy</Field.Label>
                <Select.Control value={policyId} onChange={event => {
                  const id = event.target.value;
                  setPolicyId(id);
                  setTargetIds(previous => previous.filter(value => value !== id));
                }}>
                  <Select.Option value="">Select a policy</Select.Option>
                  {documents.map(doc => <Select.Option key={doc.document_id} value={doc.document_id}>{doc.source}</Select.Option>)}
                </Select.Control>
              </Field.Root>
            </div>
            <div className="audit-step">
              <h4>2. Select contracts to review</h4>
              <p className="muted">Choose 1 to 4 contracts. Each will receive a separate review.</p>
              {loadingLibrary ? <p className="muted">Loading documents…</p> :
                libraryError ? <p role="alert" className="error-message">{libraryError}</p> :
                documents.filter(doc => doc.document_id !== policyId).length === 0 ?
                  <p className="muted">Add at least two documents to the Knowledge Base.</p> :
                  <div className="audit-document-picker">
                    {documents.filter(doc => doc.document_id !== policyId).map(doc =>
                      <div key={doc.document_id} className="audit-document-option">
                        <Field.Root id={`audit-target-${doc.document_id}`}>
                          <Input type="checkbox" checked={targetIds.includes(doc.document_id)}
                            disabled={!targetIds.includes(doc.document_id) && targetIds.length >= 4}
                            onChange={event => setTargetIds(current => event.target.checked
                              ? [...current, doc.document_id] : current.filter(id => id !== doc.document_id))}/>
                          <Field.Label><strong>{doc.source}</strong> · {doc.chunks} indexed chunks</Field.Label>
                        </Field.Root>
                      </div>)}
                  </div>}
              <p className="muted">{targetIds.length} of 4 contracts selected</p>
              {documents.length === 0 && <p className="muted">Upload your reference policy and contracts in the Knowledge Base before starting.</p>}
            </div>
            <div className="audit-step">
              <h4>3. What will be checked?</h4>
              <p>Confidentiality, personal data protection, incident notification and termination clauses.</p>
              <p className="muted">ATLAS identifies related excerpts and potential gaps. A human reviewer must confirm the findings.</p>
            </div>
          </>}
          <details className="eval-box">
            <summary>Other analyses and settings</summary>
            <Field.Root id="agent-workflow">
              <Field.Label>Analysis type</Field.Label>
              <Select.Control value={workflow}
                onChange={event => setWorkflow(event.target.value as 'tools' | 'research' | 'compliance')}>
                <Select.Option value="compliance">Contract compliance review</Select.Option>
                <Select.Option value="research">Document research</Select.Option>
                <Select.Option value="tools">Diagnostic tools</Select.Option>
              </Select.Control>
            </Field.Root>
          </details>
          <details className="eval-box">
            <summary>Additional notes (optional)</summary>
            <Field.Root id="agent-question">
              <Field.Label>Notes for the review</Field.Label>
              <Textarea rows={3} maxLength={2000} value={question}
                onChange={event => setQuestion(event.target.value)}
                placeholder="E.g., pay special attention to incident notification deadlines." />
            </Field.Root>
            <p className="muted">These notes are saved with the request. This version still uses a fixed checklist.</p>
          </details>
          <Button className="wide-button" type="submit"
            disabled={!connected || submitting || (workflow !== 'compliance' && !question.trim()) ||
              (workflow === 'compliance' && !canAudit)}>
            {submitting ? 'Starting review…' : workflow === 'compliance' ? 'Review contracts ↗' : 'Run analysis ↗'}
          </Button>
        </form>
        {!connected && <p className="inline-hint">To run agents, <Button variant="unstyled" type="button" onClick={openAccess}>connect your JWT →</Button></p>}
        {error && <p className="error-message" role="alert">{error}</p>}
        <details className="examples"><summary className="eyebrow">EXAMPLE QUESTIONS</summary>
          {examples.map(example => <Button variant="unstyled" key={example} type="button" className="example-item"
            onClick={() => setQuestion(example)}><span>{example}</span><span>↗</span></Button>)}
        </details>
        <details className="eval-box">
          <summary>How does this work? · Technical details</summary>
          <p className="muted">ATLAS queues the review in PostgreSQL. The worker retrieves only the selected policy and contracts by document ID within the authorized tenant, then runs a deterministic screening. Other modes use the agent service and MCP. This is not a legal opinion.</p>
        </details>
      </section>
      <section ref={resultsRef} className="panel results-panel" aria-live="polite">
        <div className="panel-topline"><span className="eyebrow">RESULTS</span><span className="count-chip">DOCUMENT REVIEW</span></div>
        <h3>Report & items to review</h3>
        {!jobId ? <EmptyState icon="✧" title="No review started"
          description="Select a policy and contracts to see a clear review summary." /> : <>
          <div className="result-summary"><span>✧</span><strong>Review</strong>{active && <StatusBadge status={active.status} />}</div>
          <details><summary>Technical job ID</summary><code className="job-reference">{jobId}</code></details>
          {result ? <>
            {result.compliance && result.compliance.contracts && <section className="audit-report" aria-label="Audit report">
              <span className="eyebrow">REVIEW SUMMARY</span>
              <h3>Contracts reviewed</h3>
              <p className="muted">Reference policy: <strong>{result.compliance.policy?.source}</strong></p>
              <div className="metric-pills">
                <span>Contracts: <b>{result.compliance.summary.contracts}</b></span>
                <span>Items needing attention: <b>{result.compliance.summary.needs_attention}</b></span>
                <span>Excerpts to verify: <b>{result.compliance.summary.evidence_to_review}</b></span>
              </div>
              <p>{result.compliance.disclaimer}</p>
              {result.compliance.contracts.map(contract => <article className="audit-contract" key={contract.document_id}>
                <h4>{contract.source}</h4>
                <p>{contract.summary.needs_attention > 0
                  ? `${contract.summary.needs_attention} potential issue(s) need attention. Verify the obligations before approving this contract.`
                  : contract.summary.evidence_to_review > 0
                    ? 'Relevant clauses were found. Confirm whether they fully satisfy the policy.'
                    : 'No applicable requirements could be identified automatically. Manual review is needed.'}</p>
                <div className="metric-pills">
                  <span>Potential gaps: <b>{contract.summary.needs_attention}</b></span>
                  <span>Evidence to verify: <b>{contract.summary.evidence_to_review}</b></span>
                </div>
                {contract.checks.map(check => <div key={check.id} className={`audit-finding audit-finding--${check.status}`}>
                  <strong>{check.requirement}</strong>
                  <span className="audit-status">{check.status === "needs_attention" ? "Needs attention" : check.status === "evidence_to_review" ? "Excerpt found" : "Review policy"}</span>
                  <p>{check.message}</p>
                  <details>
                    <summary>View excerpts and rationale</summary>
                    <strong>In the reference policy</strong>
                    {check.policy_evidence.length ? check.policy_evidence.map((e, i) =>
                      <p key={i} style={{ whiteSpace: 'pre-wrap' }}>{e.excerpt}<small> · {e.source} · {e.chunk_id}</small></p>)
                      : <p>No matching excerpt found.</p>}
                    <strong>In the reviewed contract</strong>
                    {check.contract_evidence.length ? check.contract_evidence.map((e, i) =>
                      <p key={i} style={{ whiteSpace: 'pre-wrap' }}>{e.excerpt}<small> · {e.source} · {e.chunk_id}</small></p>)
                      : <p>No matching excerpt found.</p>}
                  </details>
                </div>)}
              </article>)}
            </section>}
            {result.compliance && !result.compliance.contracts && <section className="answer-panel">
              <h3>Previous screening</h3>
              <p className="muted">This review ran before document selection was available. Start a new review to compare the policy and each contract separately.</p>
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
            <details className="eval-box" aria-label="Agent performance"><summary>Execution metrics</summary>
              <div className="metric-pills">
                <span>Duration: <b>{result.duration_ms.toFixed(0)} ms</b></span>
                <span>Tools: <b>{result.tool_calls}</b></span>
                <span>LLM calls: <b>{result.llm_calls}</b></span>
                <span>Planner: <b>{result.planner}</b></span>
              </div>
              <p className="muted">Duration is reported by the agent service; it excludes queue wait and frontend polling.</p>
            </details>
            <details><summary>Technical execution trace</summary>
            <div className="evidence-list">{result.trace.map((step, index) =>
              <article className="evidence-item" key={`${step.step}-${index}`}>
                <div className="evidence-heading"><span className="evidence-number">{String(index + 1).padStart(2, '0')}</span>
                  <strong>{step.step}</strong><span className="evidence-method">{step.status}</span></div>
                <p>{step.tool} · {step.duration_ms.toFixed(1)} ms</p>
              </article>)}</div></details>
          </> : active?.status === 'failed' ?
            <p className="error-message" role="alert">{active.error === 'MissingAuditDocument' ? 'A selected document is no longer available. Refresh your Knowledge Base and start a new review.' : active.error ? 'The review could not be completed. Check technical details or try again.' : 'The review could not be completed.'}</p> :
            <p className="muted">The worker is processing this job. Status refreshes automatically while jobs are active.</p>}
        </>}
        <div className="results-note"><span>ⓘ</span><p>Evidence screening is not a legal compliance verdict. Review the full documents before making decisions.</p></div>
      </section>
    </div>
    <section className="panel jobs-panel" style={{ marginTop: 22 }}>
      <div className="panel-topline"><span className="eyebrow">REVIEW HISTORY</span>
        <Button variant="unstyled" type="button" className="button-secondary" onClick={() => void refreshJobs()} disabled={!connected}>↻ Refresh</Button></div>
      {agentHistory.length === 0 ? <p className="muted">Completed agent runs will appear here during this session.</p> :
        <Table.Scroll><Table.Root className="jobs-table"><Table.Header><Table.Row>
          <Table.Head scope="col">TASK</Table.Head><Table.Head scope="col">STATUS</Table.Head><Table.Head scope="col">RESULT</Table.Head>
        </Table.Row></Table.Header><Table.Body>{agentHistory.map(job => <Table.Row key={job.id}>
          <Table.Cell className="job-prompt"><strong title={job.prompt}>{job.prompt}</strong><small>{job.id.slice(0, 8)}</small></Table.Cell>
          <Table.Cell><StatusBadge status={job.status}/></Table.Cell>
          <Table.Cell><Button variant="unstyled" type="button" className="button-secondary" onClick={() => inspect(job.id)}>View report ↗</Button></Table.Cell>
        </Table.Row>)}</Table.Body></Table.Root></Table.Scroll>}
    </section>
  </>;
}
