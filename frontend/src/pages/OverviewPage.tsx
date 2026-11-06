import { EmptyState } from '../components/EmptyState';
import { SectionHeader } from '../components/SectionHeader';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import type { View } from '../components/AppShell';
import type { Job } from '../types/jobs';
import type { KnowledgeDocument } from '../types/knowledge';
import { parseRagResult } from '../types/jobs';

interface Props {
  jobs: Job[]; documents: KnowledgeDocument[]; connected: boolean;
  navigate: (view: View) => void; openAccess: () => void;
}
export function OverviewPage({ jobs, documents, connected, navigate, openAccess }: Props) {
  const completed = jobs.filter(job => job.status === 'completed').length;
  const pending = jobs.filter(job => ['queued', 'running', 'retrying'].includes(job.status)).length;
  const evaluations = jobs.map(job => parseRagResult(job.result)?.evaluation).filter(e => e != null);
  const passed = evaluations.filter(e => e?.passed).length;
  return <>
    <div className="welcome-banner">
      <div>
        <span className="hero-kicker"><span className="hero-kicker-dot" /> YOUR AI OPERATIONS WORKSPACE</span>
        <h1>Build with context.<br/><em>Operate with confidence.</em></h1>
        <p>One workspace to index knowledge, explore retrieval and monitor every inference run.</p>
        <div className="hero-actions">
          <button className="button-primary button-large" onClick={() => navigate('playground')}>Open playground <span>↗</span></button>
          <button className="button-ghost" onClick={() => navigate('documents')}>Manage knowledge <span>→</span></button>
        </div>
      </div>
      <div className="hero-decoration" aria-hidden="true">
        <div className="orb orb-one"/><div className="orb orb-two"/><div className="orb orb-three"/>
        <span className="orb-label">RETRIEVE / REASON / EVALUATE</span>
      </div>
    </div>
    <div className="stat-grid">
      <StatCard icon="▤" label="Indexed documents" value={documents.length} meta="Stored in pgvector" tone="blue" />
      <StatCard icon="◷" label="Total runs" value={jobs.length} meta="Most recent 100 jobs" tone="purple" />
      <StatCard icon="✓" label="Completed" value={completed} meta={`${pending} still processing`} tone="green" />
      <StatCard icon="◈" label="Evaluations passed" value={passed} meta={`${evaluations.length} evaluated RAG runs`} tone="orange" />
    </div>
    <div className="overview-grid">
      <section className="panel">
        <SectionHeader eyebrow="ACTIVITY" title="Recent executions"
          action={<button className="text-button" onClick={() => navigate('jobs')}>View all ↗</button>}/>
        {!connected ? <EmptyState icon="◇" title="Connect your workspace"
          description="Provide a developer JWT to load your tenant-scoped runs."
          action={<button className="button-primary" onClick={openAccess}>Connect JWT</button>} /> :
          jobs.length === 0 ? <EmptyState icon="◷" title="No runs yet"
            description="Start with an inference prompt or ask your knowledge base a question."
            action={<button className="button-secondary" onClick={() => navigate('playground')}>Start a run →</button>} /> :
          <div className="activity-list">{jobs.slice(0, 5).map(job =>
            <div className="activity-row" key={job.id}>
              <div className="activity-icon">✧</div>
              <div className="activity-content"><strong title={job.prompt}>{job.prompt}</strong><small>{job.id.slice(0, 8)} · {job.attempts ?? 0} attempts</small></div>
              <StatusBadge status={job.status} />
            </div>)}</div>}
      </section>
      <section className="panel quick-panel">
        <SectionHeader eyebrow="QUICK START" title="Your next steps"/>
        <button className="quick-action" onClick={() => navigate('documents')}><span className="quick-icon">01</span><span><strong>Add a document</strong><small>Index a PDF or text into your knowledge base.</small></span><span>↗</span></button>
        <button className="quick-action" onClick={() => navigate('playground')}><span className="quick-icon">02</span><span><strong>Ask your knowledge</strong><small>Retrieve ranked source excerpts and citations.</small></span><span>↗</span></button>
        <button className="quick-action" onClick={() => navigate('jobs')}><span className="quick-icon">03</span><span><strong>Inspect a job</strong><small>Review status, answers and evaluation metrics.</small></span><span>↗</span></button>
        <div className="architecture-note"><span>↗</span><div><strong>Under the hood</strong><p>JWT-authenticated API → RAG / pgvector → durable worker → evaluation</p></div></div>
      </section>
    </div>
  </>;
}
