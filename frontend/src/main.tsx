import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AccessDialog } from './components/AccessDialog';
import { AppShell, type View } from './components/AppShell';
import { useJobs } from './hooks/useJobs';
import { useKnowledge } from './hooks/useKnowledge';
import { DocumentsPage } from './pages/DocumentsPage';
import { JobsPage } from './pages/JobsPage';
import { OverviewPage } from './pages/OverviewPage';
import { PlaygroundPage } from './pages/PlaygroundPage';
import './style.css';

function App() {
  const [view, setView] = useState<View>('overview');
  const [token, setToken] = useState('');
  const [showAccess, setShowAccess] = useState(false);
  const { jobs, isLoading: jobsLoading, error: jobsError, refresh: refreshJobs } = useJobs(token);
  const knowledge = useKnowledge(token);
  const connected = Boolean(token.trim());

  useEffect(() => {
    if (connected) {
      void refreshJobs();
      void knowledge.refresh();
    }
    // Explicitly refresh when the identity changes, not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!connected || !jobs.some(job => ['queued', 'running', 'retrying'].includes(job.status))) return;
    const interval = setInterval(() => { void refreshJobs(); }, 4000);
    return () => clearInterval(interval);
  }, [connected, jobs, refreshJobs]);

  const openAccess = () => setShowAccess(true);
  return <>
    <AppShell view={view} onNavigate={setView} connected={connected} onOpenAccess={openAccess}>
      {(jobsError && view === 'overview') && <div className="global-alert" role="alert">{jobsError}</div>}
      {(knowledge.error && view === 'overview') && <div className="global-alert" role="alert">{knowledge.error}</div>}
      {view === 'overview' && <OverviewPage jobs={jobs} documents={knowledge.documents} connected={connected}
        navigate={setView} openAccess={openAccess}/>}
      {view === 'documents' && <DocumentsPage token={token} connected={connected}
        documents={knowledge.documents} loading={knowledge.loading} busy={knowledge.busy} error={knowledge.error}
        mutate={knowledge.mutate} refresh={knowledge.refresh} openAccess={openAccess}/>}
      {view === 'playground' && <PlaygroundPage token={token} connected={connected} jobs={jobs}
        refreshJobs={refreshJobs} openAccess={openAccess}/>}
      {view === 'jobs' && <JobsPage token={token} connected={connected} jobs={jobs} loading={jobsLoading}
        onRefresh={refreshJobs} openAccess={openAccess}/>}
    </AppShell>
    {showAccess && <AccessDialog token={token} onChange={setToken} onClose={() => setShowAccess(false)}
      onConnected={() => {}}/>}
  </>;
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
