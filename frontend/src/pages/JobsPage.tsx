import { useState } from 'react';
import { Table } from '../components/ui';
import { Button, Field, Input, Tabs } from '../components/ui';
import { EmptyState } from '../components/EmptyState';
import { SectionHeader } from '../components/SectionHeader';
import { StatusBadge } from '../components/StatusBadge';
import { jobsApi } from '../lib/api';
import type { Job } from '../types/jobs';
import { parseRagResult } from '../types/jobs';

interface Props {
  token: string; connected: boolean; jobs: Job[]; loading: boolean;
  onRefresh: () => Promise<void>; openAccess: () => void;
}
export function JobsPage({ token, connected, jobs, loading, onRefresh, openAccess }: Props) {
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'failed'>('all');
  const [prompt, setPrompt] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const filtered = jobs.filter(job => filter === 'all' ? true :
    filter === 'active' ? ['queued', 'running', 'retrying'].includes(job.status) : job.status === filter);

  async function submit() {
    if (!prompt.trim() || !connected) return;
    setSubmitting(true); setError(null);
    try {
      await jobsApi.createInference(token, prompt.trim());
      setPrompt('');
      await onRefresh();
    } catch (failure: unknown) {
      setError(failure instanceof Error ? failure.message : 'Could not submit job');
    } finally { setSubmitting(false); }
  }
  return <>
    <SectionHeader eyebrow="EXECUTION HISTORY" title="Job runs"
      description="Watch your durable worker queue, inspect completed answers and review evaluation outcomes."
      action={<Button variant="unstyled" className="button-secondary" onClick={() => void onRefresh()} disabled={!connected || loading}>{loading ? 'Refreshing…' : '↻ Refresh jobs'}</Button>}/>
    <section className="panel quick-job">
      <div><span className="eyebrow">QUICK INFERENCE</span><h3>Run a test prompt</h3><p className="muted">The default inference worker transforms the input to uppercase for a deterministic end-to-end demo.</p></div>
      <div className="quick-job-form"><Field.Root id="inference-prompt"><Field.Label className="sr-only">Inference prompt</Field.Label><Input maxLength={8000} value={prompt}
        onChange={event => setPrompt(event.target.value)} placeholder="Type an inference prompt…"
        onKeyDown={event => { if (event.key === 'Enter') void submit(); }} /></Field.Root>
        <Button type="button" disabled={!connected || submitting || !prompt.trim()}
          onClick={() => void submit()}>{submitting ? 'Queuing…' : 'Run inference ↗'}</Button></div>
      {error && <p role="alert" className="error-message">{error}</p>}
      {!connected && <p className="inline-hint">Connect to run inference. <Button variant="unstyled" onClick={openAccess}>Connect JWT →</Button></p>}
    </section>
    <section className="panel jobs-panel">
      <div className="jobs-toolbar"><div><span className="eyebrow">RECENT ACTIVITY</span><h3>Execution log <span className="count-chip">{jobs.length}</span></h3></div>
        <Tabs.Root value={filter} onValueChange={value => setFilter(value as typeof filter)}>
          <Tabs.List className="filter-tabs" aria-label="Filter jobs">
            {(['all','active','completed','failed'] as const).map(item =>
              <Tabs.Trigger key={item} value={item}>{item}</Tabs.Trigger>)}
          </Tabs.List>
        </Tabs.Root>
      </div>
      {!connected ? <EmptyState icon="◇" title="Connect to view jobs" description="Job history is scoped to the authenticated tenant." /> :
        filtered.length === 0 ? <EmptyState icon="◷" title="No matching executions" description="New runs appear here after submission. Change the filter to view other jobs." /> :
        <Table.Scroll><Table.Root className="jobs-table">
          <Table.Header><Table.Row><Table.Head scope="col">PROMPT</Table.Head><Table.Head scope="col">STATUS</Table.Head><Table.Head scope="col">ATTEMPTS</Table.Head><Table.Head scope="col">RESULT / EVALUATION</Table.Head></Table.Row></Table.Header>
          <Table.Body>{filtered.map(job => {
            const rag = parseRagResult(job.result);
            return <Table.Row key={job.id}>
              <Table.Cell className="job-prompt"><strong title={job.prompt}>{job.prompt}</strong><small>{job.id.slice(0, 8)} · {job.created_at ? new Date(job.created_at).toLocaleString() : 'Job'}</small></Table.Cell>
              <Table.Cell><StatusBadge status={job.status}/></Table.Cell>
              <Table.Cell className="attempt-cell">{job.attempts ?? 0}</Table.Cell>
              <Table.Cell><div className="job-result">{rag ? <>
                <span title={rag.answer}>{rag.answer}</span>
                <small>{rag.citations.length} cited source(s) · {rag.mode.replaceAll('_', ' ')}</small>
                {rag.evaluation && <small className={rag.evaluation.passed ? 'eval-passed' : 'eval-failed'}>
                  {rag.evaluation.passed ? '✓ Evaluation passed' : '✕ Evaluation failed'}</small>}
              </> : <span title={job.result || job.error || ''}>{job.result || job.error || '—'}</span>}</div></Table.Cell>
            </Table.Row>;
          })}</Table.Body>
        </Table.Root></Table.Scroll>}
    </section>
  </>;
}
