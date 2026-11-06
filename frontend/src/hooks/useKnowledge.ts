import { useCallback, useEffect, useRef, useState } from 'react';
import { knowledgeApi } from '../lib/knowledgeApi';
import type { KnowledgeDocument } from '../types/knowledge';

export function useKnowledge(token: string) {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentToken = useRef(token);
  currentToken.current = token;
  const generation = useRef(0);

  const refresh = useCallback(async () => {
    if (!token.trim()) return;
    const expected = ++generation.current;
    setLoading(true);
    setError(null);
    try {
      const response = await knowledgeApi.list(token);
      if (expected === generation.current && currentToken.current === token) setDocuments(response.items);
    } catch (failure: unknown) {
      if (expected === generation.current && currentToken.current === token) {
        setError(failure instanceof Error ? failure.message : 'Could not load documents');
      }
    } finally {
      if (expected === generation.current) setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    ++generation.current;
    setDocuments([]);
    setError(null);
    setLoading(false);
  }, [token]);

  const mutate = useCallback(async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
      return true;
    } catch (failure: unknown) {
      if (currentToken.current === token) {
        setError(failure instanceof Error ? failure.message : 'Knowledge request failed');
      }
      return false;
    } finally {
      setBusy(false);
    }
  }, [refresh, token]);

  return { documents, loading, busy, error, refresh, mutate, setError };
}
