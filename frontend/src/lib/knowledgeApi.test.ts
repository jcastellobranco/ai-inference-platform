import { afterEach, describe, expect, it, vi } from 'vitest';
import { knowledgeApi } from './knowledgeApi';

afterEach(() => vi.unstubAllGlobals());

describe('knowledge gateway client', () => {
  it('requires a developer JWT', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await expect(knowledgeApi.list('')).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('sends document ingestion only to the authenticated BFF', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ document_id: 'id', chunks: 2 }) });
    vi.stubGlobal('fetch', fetchMock);
    await knowledgeApi.ingestText('dev-token', 'notes.md', 'Testing pgvector');
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/v1/knowledge/documents');
    expect(options.headers.Authorization).toBe('Bearer dev-token');
    expect(JSON.parse(options.body)).toEqual({ source: 'notes.md', text: 'Testing pgvector' });
    expect(options.headers).not.toHaveProperty('x-api-key');
  });
  it('uploads a PDF without forcing JSON content-type', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ document_id: 'id', chunks: 1 }) });
    vi.stubGlobal('fetch', fetchMock);
    const pdf = new File(['%PDF-test'], 'report.pdf', { type: 'application/pdf' });
    await knowledgeApi.uploadPdf('test-token', pdf);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain('/v1/knowledge/documents/pdf');
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.headers).not.toHaveProperty('Content-Type');
  });
  it('returns a helpful error for an unavailable RAG service', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502 }));
    await expect(knowledgeApi.list('token')).rejects.toThrow(/integrated Compose/);
  });
});
