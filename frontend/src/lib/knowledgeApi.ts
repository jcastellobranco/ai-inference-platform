import type { IngestReceipt, KnowledgeDocument, SearchResponse } from '../types/knowledge';
import { ApiError } from './api';

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) || '/api';

async function call<T>(
  path: string, token: string, options: RequestInit = {},
): Promise<T> {
  if (!token.trim()) throw new ApiError(401, 'Connect your development JWT first.');
  const response = await fetch(BASE_URL + path, {
    ...options,
    headers: {
      Authorization: `Bearer ${token.trim()}`,
      ...options.headers,
    },
  });
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new ApiError(response.status, 'Your session is invalid or this tenant has no RAG access.');
    }
    if (response.status === 413) throw new ApiError(413, 'PDF exceeds the 10 MiB limit.');
    if (response.status === 415) throw new ApiError(415, 'Only PDF files are accepted.');
    if (response.status === 503 || response.status === 502) {
      throw new ApiError(response.status, 'Knowledge service is unavailable. Start the integrated Compose stack.');
    }
    throw new ApiError(response.status, `Request failed (HTTP ${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const knowledgeApi = {
  list: (token: string) =>
    call<{ items: KnowledgeDocument[] }>('/v1/knowledge/documents', token),
  ingestText: (token: string, source: string, text: string) =>
    call<IngestReceipt>('/v1/knowledge/documents', token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, text }),
    }),
  uploadPdf: (token: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return call<IngestReceipt>('/v1/knowledge/documents/pdf', token, {
      method: 'POST',
      body: form,
    });
  },
  remove: (token: string, id: string) =>
    call<{ deleted: boolean }>(`/v1/knowledge/documents/${encodeURIComponent(id)}`, token, {
      method: 'DELETE',
    }),
  search: (token: string, question: string, limit = 5) =>
    call<SearchResponse>('/v1/knowledge/search', token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, limit }),
    }),
};
