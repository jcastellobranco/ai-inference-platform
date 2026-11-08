import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Button, Field, Textarea } from '../components/ui';
import { EmptyState } from '../components/EmptyState';
import { SectionHeader } from '../components/SectionHeader';
import { StatusBadge } from '../components/StatusBadge';
import { jobsApi } from '../lib/api';
import { knowledgeApi } from '../lib/knowledgeApi';
import type { Job } from '../types/jobs';
import { parseRagResult } from '../types/jobs';
import type { SearchHit } from '../types/knowledge';

const examples = [
  'Summarize the key ideas in my documents',
  'What are the deployment requirements?',
  'How does tenant isolation work?',
];

interface Props {
  token: string; connected: boolean; jobs: Job[];
  refreshJobs: () => Promise<void>; openAccess: () => void;
}
export function PlaygroundPage({ token, connected, jobs, refreshJobs, openAccess }: Props) {
  const [question, setQuestion] = useState('');
  const [reference, setReference] = useState('');
  const [conversationContext, setConversationContext] = useState('');
  const [mode, setMode] = useState<'retrieve' | 'rag'>('rag');
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentToken = useRef(token);
  currentToken.current = token;
  const activeJob = jobs.find(job => job.id === jobId);
  const answer = activeJob ? parseRagResult(activeJob.result) : null;
  useEffect(() => { setHits(null); setJobId(null); setError(null); setBusy(false); setConversationContext(''); }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!connected || busy || !question.trim()) return;
    const submittedToken = token;
    setBusy(true); setError(null); setHits(null); setJobId(null);
    try {
      if (mode === 'retrieve') {
        const result = await knowledgeApi.search(token, question.trim());
        if (currentToken.current === submittedToken) setHits(result.citations);
      } else {
        const standaloneQuestion = conversationContext.trim()
          ? `Previous question: ${conversationContext.trim()}\nCurrent question: ${question.trim()}\nAnswer only the current question using document evidence.`
          : question.trim();
        const result = await jobsApi.createRag(token, standaloneQuestion.slice(0, 2000), reference.trim() || undefined);
        if (currentToken.current === submittedToken) {
          setJobId(result.id);
          setConversationContext(question.trim());
          await refreshJobs();
        }
      }
    } catch (failure: unknown) {
      if (currentToken.current === submittedToken) setError(failure instanceof Error ? failure.message : 'Request failed');
    } finally {
      if (currentToken.current === submittedToken) setBusy(false);
    }
  }

  return <>
    <SectionHeader eyebrow="RETRIEVAL LAB" title="RAG playground"
      description="Explore hybrid retrieval against your indexed sources, or send a question through the durable RAG worker." />
    <div className="playground-grid">
      <section className="panel query-panel">
        <div className="panel-topline"><span className="eyebrow">QUERY BUILDER</span><span className="step-chip">02 / EXPLORE</span></div>
        <h3>Ask better questions.</h3><p className="muted">Query your indexed content with lexical and semantic search combined using Reciprocal Rank Fusion.</p>
        <div className="mode-switch" role="group" aria-label="Query mode">
          <button type="button" className={mode === 'retrieve' ? 'selected' : ''} onClick={() => setMode('retrieve')}>⌕ Inspect retrieval</button>
          <button type="button" className={mode === 'rag' ? 'selected' : ''} onClick={() => setMode('rag')}>✧ Ask AI</button>
        </div>
        <form onSubmit={event => void submit(event)}>
          {conversationContext && mode === 'rag' && <p className="inline-hint">Previous question: {conversationContext.slice(0, 160)} <button type="button" onClick={() => setConversationContext('')}>Clear context</button></p>}
          <Field.Root id="query-question"><Field.Label>Your question</Field.Label>
          <Textarea rows={6} maxLength={2000} value={question}
            onChange={event => setQuestion(event.target.value)}
            placeholder="What would you like to know about your documents?" required /></Field.Root>
          {mode === 'rag' && <>
            <Field.Root id="query-reference"><Field.Label>Expected answer <span className="optional">OPTIONAL · ENABLES EVALUATION</span></Field.Label>
            <Textarea rows={3} maxLength={16000} value={reference}
              onChange={event => setReference(event.target.value)} placeholder="Provide a reference to measure exact match and token F1." /></Field.Root>
          </>}
          <Button type="submit" className="wide-button" disabled={!connected || busy || !question.trim()}>
            {busy ? 'Processing…' : mode === 'retrieve' ? 'Search knowledge base' : 'Ask AI · queue job'} <span>↗</span>
          </Button>
        </form>
        {!connected && <p className="inline-hint">To query your documents, <button onClick={openAccess}>connect your JWT →</button></p>}
        {error && <p className="error-message" role="alert">{error}</p>}
        <div className="examples"><span className="eyebrow">TRY A PROMPT</span>
          {examples.map(example => <button key={example} type="button" className="example-item" onClick={() => setQuestion(example)}>
            <span>{example}</span><span>↗</span>
          </button>)}
        </div>
      </section>
      <section className="panel results-panel">
        <div className="panel-topline"><span className="eyebrow">OUTPUT</span><span className="count-chip">LIVE RESULTS</span></div>
        <h3>Results & evidence</h3>
        {!hits && !jobId ? <EmptyState icon="✧" title="Your results will appear here"
          description="Enter a question to inspect ranked source excerpts and cited RAG answers."/> : null}
        {hits && <>
          <div className="result-summary"><span>✓</span><strong>{hits.length} source{hits.length === 1 ? '' : 's'} retrieved</strong><small>Hybrid RRF ranking</small></div>
          {hits.length === 0 ? <EmptyState icon="⌕" title="No matching evidence" description="Index some documents or try another question."/> :
            <div className="evidence-list">{hits.map((hit, index) =>
              <article key={hit.chunk_id} className="evidence-item">
                <div className="evidence-heading"><span className="evidence-number">{String(index + 1).padStart(2, '0')}</span><strong>{hit.source}</strong><span className="evidence-method">{hit.method}</span></div>
                <p>{hit.text}</p>
                <div className="evidence-footer"><span>Chunk {hit.chunk_id.slice(0, 8)}</span><span>RRF {hit.score.toFixed(4)}</span></div>
              </article>)}</div>}
        </>}
        {jobId && <div className="rag-output">
          <div className="result-summary"><span>✧</span><strong>RAG job submitted</strong>{activeJob && <StatusBadge status={activeJob.status}/>}</div>
          <code className="job-reference">{jobId}</code>
          {answer ? <>
            <div className="answer-panel"><span className="eyebrow">ANSWER · {answer.mode.replaceAll('_', ' ').toUpperCase()}</span><p>{answer.answer}</p></div>
            {answer.model && <p className="muted">Model: {answer.model}{answer.usage?.input_tokens != null ? ` · Input: ${answer.usage.input_tokens} tokens` : ''}{answer.usage?.output_tokens != null ? ` · Output: ${answer.usage.output_tokens} tokens` : ''}</p>}
            {answer.retrieval && <p className="muted">Retrieval: {answer.retrieval.chunks_found} chunks · {answer.retrieval.sources.length} document(s) · Status: {answer.answer_status || "answered"}</p>}
            {answer.performance && <section className="eval-box" aria-label="Performance trace">
              <strong>Performance trace · {(answer.performance.processing_ms / 1000).toFixed(2)}s processing</strong>
              <div className="metric-pills">
                <span>Retrieval: <b>{answer.performance.retrieval_ms.toFixed(0)} ms</b></span>
                <span>LLM: <b>{answer.performance.generation_ms.toFixed(0)} ms</b></span>
                <span>Evaluation: <b>{answer.performance.evaluation_ms.toFixed(0)} ms</b></span>
                <span>Provider calls: <b>{answer.performance.provider_calls}</b></span>
                <span>Citation repair: <b>{answer.performance.repair_attempted ? 'yes' : 'no'}</b></span>
              </div>
              <p className="muted">Processing time excludes queue waiting and frontend polling. Older jobs may not include a trace.</p>
            </section>}
            <h4>Referenced sources</h4>
            {answer.citations.map((citation, index) => <div className="citation-row" key={citation.chunk_id}>
              <span>[{index + 1}]</span><strong>{citation.source}</strong><small>{citation.chunk_id.slice(0, 8)}</small>
            </div>)}
            {answer.evaluation && <div className="eval-box"><strong>{answer.evaluation.passed ? '✓ Evaluation passed' : '✕ Evaluation failed'}</strong>
              <div className="metric-pills">{Object.entries(answer.evaluation.metrics).map(([key, value]) =>
                <span key={key}>{key.replaceAll('_', ' ')}: <b>{typeof value === 'number' ? value.toFixed(2) : value}</b></span>)}</div>
            </div>}
          </> : activeJob?.status === 'failed' ? <p className="error-message">{activeJob.error || 'Job failed'}</p>
            : <p className="muted">Worker is processing your question. Results update automatically while the job is active.</p>}
        </div>}
        <div className="results-note"><span>ⓘ</span><p>Ask AI runs a durable RAG job. Until an external API key is configured, answers are extractive (first retrieved chunk), not LLM-generated. Inspect retrieval shows the ranked evidence.</p></div>
      </section>
    </div>
  </>;
}
