import type { Job } from '../types/jobs';

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) || '/api';
export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}
async function request<T>(
  path: string, token: string, options: RequestInit = {}, signal?: AbortSignal,
): Promise<T> {

  const response = await fetch(BASE_URL + path, {
    ...options,
    signal,
    credentials: 'same-origin',
    headers: {
      ...((typeof document !== 'undefined' ? document.cookie : '').match(/(?:^|; )atlas_csrf=([^;]*)/)?.[1] && !['GET','HEAD'].includes(options.method || 'GET') ? { 'X-CSRF-Token': decodeURIComponent((typeof document !== 'undefined' ? document.cookie : '').match(/(?:^|; )atlas_csrf=([^;]*)/)![1]) } : {}),
      ...(token.trim() && token !== 'browser-session' ? { Authorization: `Bearer ${token.trim()}` } : {}),
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Request failed (HTTP ${response.status})`);
  }
  return response.json() as Promise<T>;
}
export const jobsApi = {
  list: (token: string, signal?: AbortSignal) =>
    request<{ items: Job[] }>('/v1/jobs', token, {}, signal),
  createInference: (token: string, prompt: string) =>
    request<{ id: string; status: string }>('/v1/jobs', token, {
      method: 'POST', body: JSON.stringify({ prompt }),
    }),
  createAgent: (token: string, question: string, workflow: 'tools' | 'research' | 'compliance' = 'tools', selection?: { policy_document_id: string; target_document_ids: string[] }) =>
    request<{ id: string; status: string; job_type: 'agent' }>('/v1/agent/jobs', token, {
      method: 'POST', body: JSON.stringify({ question, workflow, ...(selection || {}) }),
    }),
  createRag: (token: string, question: string, referenceAnswer?: string) =>
    request<{ id: string; status: string; job_type: string }>('/v1/rag/jobs', token, {
      method: 'POST',
      body: JSON.stringify({ question, ...(referenceAnswer ? { reference_answer: referenceAnswer } : {}) }),
    }),
};
