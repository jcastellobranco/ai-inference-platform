import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AccessTokenPanel } from './components/AccessTokenPanel';
import { JobForm } from './components/JobForm';
import { JobsTable } from './components/JobsTable';
import { useJobs } from './hooks/useJobs';
import { jobsApi } from './lib/api';
import type { JobType } from './types/jobs';
import './style.css';

function App() {
  const [token, setToken] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const { jobs, isLoading, error, refresh } = useJobs(token);

  async function submit(type: JobType, prompt: string, reference: string) {
    setIsSubmitting(true);
    setSubmissionError(null);
    try {
      if (type === 'rag') await jobsApi.createRag(token, prompt, reference || undefined);
      else await jobsApi.createInference(token, prompt);
      await refresh();
    } catch (failure: unknown) {
      setSubmissionError(failure instanceof Error ? failure.message : 'Job submission failed');
    } finally {
      setIsSubmitting(false);
    }
  }

  return <main>
    <header className="page-header">
      <p className="eyebrow">Developer console</p>
      <h1>AI Platform Console</h1>
      <p>Tenant-isolated inference jobs, document retrieval and evaluation.</p>
    </header>
    <AccessTokenPanel token={token} onTokenChange={setToken} onLoad={() => void refresh()}
      isLoading={isLoading} />
    <JobForm disabled={!token.trim()} isSubmitting={isSubmitting} onSubmit={submit} />
    {(error || submissionError) && <p className="alert" role="alert">{submissionError || error}</p>}
    <JobsTable jobs={jobs} isLoading={isLoading} onRefresh={() => void refresh()}
      disabled={!token.trim()} />
    <footer>Developer preview · JWT is held in memory only · No production login flow</footer>
  </main>;
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
