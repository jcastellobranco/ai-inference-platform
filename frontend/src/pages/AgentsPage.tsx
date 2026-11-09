import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Table } from '../components/ui';
import { Button, Field, Select, Textarea } from '../components/ui';
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
  'Verifique evidências de confidencialidade, proteção de dados, incidentes e rescisão nos documentos indexados',
  'Analyze this request using the available local tools',
  'Test the ATLAS agent execution pipeline',
];

export function AgentsPage({ token, connected, jobs, refreshJobs, openAccess }: Props) {
  const [question, setQuestion] = useState('Review supplier documents for confidentiality, incident notification, personal data protection and termination requirements.');
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [policyId, setPolicyId] = useState('');
  const [targetIds, setTargetIds] = useState<string[]>([]);
  const [libraryError, setLibraryError] = useState<string | null>(null);
  const [loadingLibrary, setLoadingLibrary] = useState(false);
  const [workflow, setWorkflow] = useState<'tools' | 'research' | 'compliance'>('compliance');
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tokenRef = useRef(token);
  tokenRef.current = token;

  useEffect(() => {
    setQuestion('Review supplier documents for confidentiality, incident notification, personal data protection and termination requirements.');
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
  const agentHistory = jobs.filter(job => parseAgentResult(job.result) !== null ||
    (jobId !== null && job.id === jobId));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!connected || submitting || !trimmed || trimmed.length > 2000 || (workflow === "compliance" && !canAudit)) return;
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
        <div className="panel-topline"><span className="eyebrow">NEW REVIEW</span><span className="step-chip">EARLY ACCESS</span></div>
        <h3>Review contractual requirements</h3>
        <p className="muted">Compare seus contratos com uma política corporativa e descubra quais pontos merecem atenção antes da aprovação.</p>
        <form onSubmit={event => void submit(event)}>
          {workflow === 'compliance' && <>
            <div className="eval-box">
              <h4>1. Qual política devemos seguir?</h4>
              <p className="muted">Escolha o documento que estabelece as obrigações e regras de referência.</p>
              <Field.Root id="audit-policy">
                <Field.Label>Política de referência</Field.Label>
                <Select.Control value={policyId} onChange={event => {
                  const id = event.target.value;
                  setPolicyId(id);
                  setTargetIds(previous => previous.filter(value => value !== id));
                }}>
                  <Select.Option value="">Selecione uma política</Select.Option>
                  {documents.map(doc => <Select.Option key={doc.document_id} value={doc.document_id}>{doc.source}</Select.Option>)}
                </Select.Control>
              </Field.Root>
            </div>
            <div className="eval-box">
              <h4>2. Quais documentos deseja analisar?</h4>
              <p className="muted">Escolha de 1 a 4 contratos. Cada contrato será analisado separadamente.</p>
              {loadingLibrary ? <p className="muted">Carregando documentos…</p> :
                libraryError ? <p role="alert" className="error-message">{libraryError}</p> :
                documents.filter(doc => doc.document_id !== policyId).length === 0 ?
                  <p className="muted">Adicione pelo menos dois documentos na Knowledge Base.</p> :
                  <div className="document-list">
                    {documents.filter(doc => doc.document_id !== policyId).map(doc =>
                      <label key={doc.document_id} className="document-row">
                        <input type="checkbox" checked={targetIds.includes(doc.document_id)}
                          disabled={!targetIds.includes(doc.document_id) && targetIds.length >= 4}
                          onChange={event => setTargetIds(current => event.target.checked
                            ? [...current, doc.document_id] : current.filter(id => id !== doc.document_id))}/>
                        <span className="file-info"><strong>{doc.source}</strong><small>{doc.chunks} trechos indexados</small></span>
                      </label>)}
                  </div>}
              <p className="muted">{targetIds.length} de 4 documentos selecionados</p>
              {documents.length === 0 && <p className="muted">Acesse Knowledge Base e envie a política e os contratos antes de iniciar.</p>}
            </div>
            <div className="eval-box">
              <h4>3. O que será verificado?</h4>
              <p>Confidencialidade, proteção de dados pessoais, comunicação de incidentes e condições de rescisão.</p>
              <p className="muted">O ATLAS localizará trechos relacionados e destacará possíveis lacunas. A conclusão requer revisão humana.</p>
            </div>
          </>}
          <details className="eval-box">
            <summary>Outras análises e configurações</summary>
            <Field.Root id="agent-workflow">
              <Field.Label>Tipo de análise</Field.Label>
              <Select.Control value={workflow}
                onChange={event => setWorkflow(event.target.value as 'tools' | 'research' | 'compliance')}>
                <Select.Option value="compliance">Auditoria de contratos</Select.Option>
                <Select.Option value="research">Pesquisa nos documentos</Select.Option>
                <Select.Option value="tools">Ferramentas de diagnóstico</Select.Option>
              </Select.Control>
            </Field.Root>
          </details>
          <details className="eval-box">
            <summary>Orientações adicionais (opcional)</summary>
            <Field.Root id="agent-question">
              <Field.Label>Orientações para o relatório</Field.Label>
              <Textarea rows={3} maxLength={2000} value={question}
                onChange={event => setQuestion(event.target.value)}
                placeholder="Ex.: dê atenção especial aos prazos de notificação de incidentes." />
            </Field.Root>
            <p className="muted">No checklist atual, as regras são fixas; esse texto é registrado na solicitação e não altera os critérios.</p>
          </details>
          <Button className="wide-button" type="submit"
            disabled={!connected || submitting || !question.trim() ||
              (workflow === 'compliance' && !canAudit)}>
            {submitting ? 'Iniciando análise…' : workflow === 'compliance' ? 'Analisar contratos ↗' : 'Executar análise ↗'}
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
          <p className="muted">ATLAS queues a tenant-bound PostgreSQL job. The worker calls the research agent, which retrieves RAG evidence and returns a source-backed checklist. Execution traces remain available for troubleshooting.</p>
        </details>
      </section>
      <section className="panel results-panel" aria-live="polite">
        <div className="panel-topline"><span className="eyebrow">REVIEW RESULTS</span><span className="count-chip">AUDIT TRAIL</span></div>
        <h3>Findings & evidence</h3>
        {!jobId ? <EmptyState icon="✧" title="No review selected"
          description="Start a compliance screening to see findings and source evidence." /> : <>
          <div className="result-summary"><span>✧</span><strong>Review job</strong>{active && <StatusBadge status={active.status} />}</div>
          <code className="job-reference">{jobId}</code>
          {result ? <>
            {result.compliance && result.compliance.contracts && <section className="answer-panel" aria-label="Relatório de auditoria">
              <span className="eyebrow">RESULTADO DA ANÁLISE</span>
              <h3>Contratos analisados</h3>
              <p className="muted">Política de referência: <strong>{result.compliance.policy?.source}</strong></p>
              <div className="metric-pills">
                <span>Contratos: <b>{result.compliance.summary.contracts}</b></span>
                <span>Pontos de atenção: <b>{result.compliance.summary.needs_attention}</b></span>
                <span>Trechos para conferir: <b>{result.compliance.summary.evidence_to_review}</b></span>
              </div>
              <p>{result.compliance.disclaimer}</p>
              {result.compliance.contracts.map(contract => <article className="eval-box" key={contract.document_id}>
                <h4>{contract.source}</h4>
                <p>{contract.summary.needs_attention > 0
                  ? `Foram encontrados ${contract.summary.needs_attention} possível(is) ponto(s) de atenção. Confira as obrigações antes de aprovar.`
                  : contract.summary.evidence_to_review > 0
                    ? 'Foram encontrados trechos relacionados aos requisitos. Confirme se são suficientes.'
                    : 'Não foi possível identificar requisitos aplicáveis de forma automática.'}</p>
                <div className="metric-pills">
                  <span>Revisar possível lacuna: <b>{contract.summary.needs_attention}</b></span>
                  <span>Verificar evidências: <b>{contract.summary.evidence_to_review}</b></span>
                </div>
                {contract.checks.map(check => <div key={check.id} className="evidence-item">
                  <strong>{check.requirement}</strong>
                  <p>{check.message}</p>
                  <details>
                    <summary>Ver trechos e justificativa</summary>
                    <strong>Na política de referência</strong>
                    {check.policy_evidence.length ? check.policy_evidence.map((e, i) =>
                      <p key={i} style={{ whiteSpace: 'pre-wrap' }}>{e.excerpt}<small> · {e.source} · {e.chunk_id}</small></p>)
                      : <p>Nenhum trecho localizado.</p>}
                    <strong>No contrato analisado</strong>
                    {check.contract_evidence.length ? check.contract_evidence.map((e, i) =>
                      <p key={i} style={{ whiteSpace: 'pre-wrap' }}>{e.excerpt}<small> · {e.source} · {e.chunk_id}</small></p>)
                      : <p>Nenhum trecho localizado.</p>}
                  </details>
                </div>)}
              </article>)}
            </section>}
            {result.compliance && !result.compliance.contracts && <section className="answer-panel">
              <h3>Triagem anterior</h3>
              <p className="muted">Esta execução foi feita antes da seleção de documentos. Inicie uma nova análise para comparar política e contratos separadamente.</p>
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
            <p className="error-message" role="alert">{active.error || 'Agent execution failed'}</p> :
            <p className="muted">The worker is processing this job. Status refreshes automatically while jobs are active.</p>}
        </>}
        <div className="results-note"><span>ⓘ</span><p>Evidence screening is not a legal compliance verdict. Review the full documents before making decisions.</p></div>
      </section>
    </div>
    <section className="panel jobs-panel" style={{ marginTop: 22 }}>
      <div className="panel-topline"><span className="eyebrow">RECENT REVIEWS</span>
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
