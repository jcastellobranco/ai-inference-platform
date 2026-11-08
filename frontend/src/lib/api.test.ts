import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, jobsApi } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('jobsApi', () => {
  it('rejects calls without a token before accessing the network', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await expect(jobsApi.list('')).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('sends a JWT and a typed RAG request', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'job-1', status: 'queued', job_type: 'rag' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const response = await jobsApi.createRag('token-123', 'What is RLS?', 'Row-level security');
    expect(response.job_type).toBe('rag');
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain('/v1/rag/jobs');
    expect(options.headers.Authorization).toBe('Bearer token-123');
    expect(JSON.parse(options.body)).toEqual({
      question: 'What is RLS?', reference_answer: 'Row-level security',
    });
  });

  it('submits an agent task to the authenticated ATLAS job endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'agent-1', status: 'queued', job_type: 'agent' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const response = await jobsApi.createAgent('tenant-jwt', 'Count three words');
    expect(response.job_type).toBe('agent');
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain('/v1/agent/jobs');
    expect(options.headers.Authorization).toBe('Bearer tenant-jwt');
    expect(JSON.parse(options.body)).toEqual({ question: 'Count three words' });
  });

  it('reports HTTP failures without leaking response content', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403 }));
    await expect(jobsApi.list('restricted-token')).rejects.toMatchObject({ status: 403 });
  });
});
