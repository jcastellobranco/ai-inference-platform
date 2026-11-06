import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Job = { id: string; prompt: string; status: string };
const API = import.meta.env.VITE_API_URL || '/api';
function App() {
  const [token, setToken] = useState('');
  const [prompt, setPrompt] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState('');
  const headers = { Authorization: 'Bearer ' + token };
  async function refresh() {
    const response = await fetch(API + '/v1/jobs', { headers });
    if (!response.ok) throw new Error('Request failed: ' + response.status);
    setJobs((await response.json()).items);
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const response = await fetch(API + '/v1/jobs', { method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt }) });
      if (!response.ok) throw new Error('Submission failed: ' + response.status);
      setPrompt(''); await refresh(); setError('');
    } catch (e) { setError(String(e)); }
  }
  return <main><header><h1>AI Platform Console</h1><p>Multi-tenant inference operations · developer preview</p></header>
    <section><h2>Development token</h2><p>Paste a short-lived JWT for local testing. Token is held in component memory only.</p><input aria-label="JWT" type="password" value={token} onChange={e => setToken(e.target.value)} placeholder="JWT access token"/><button onClick={() => refresh().catch(e => setError(String(e)))}>Load jobs</button></section>
    <section><h2>Submit inference job</h2><form onSubmit={submit}><textarea aria-label="Prompt" maxLength={8000} value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Enter prompt"/><button disabled={!token || !prompt.trim()}>Submit</button></form></section>
    {error && <p role="alert">{error}</p>}<section><h2>Recent jobs</h2><table><thead><tr><th>Job ID</th><th>Prompt</th><th>Status</th></tr></thead><tbody>{jobs.map(j => <tr key={j.id}><td>{j.id}</td><td>{j.prompt}</td><td>{j.status}</td></tr>)}</tbody></table></section>
  </main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
