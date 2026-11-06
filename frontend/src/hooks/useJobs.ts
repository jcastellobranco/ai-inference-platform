import { useCallback, useEffect, useRef, useState } from 'react';
import { jobsApi } from '../lib/api';
import type { Job } from '../types/jobs';

export function useJobs(token: string) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    if (!token.trim()) {
      setJobs([]); setError(null); setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await jobsApi.list(token, controller.signal);
      if (!controller.signal.aborted) setJobs(response.items);
    } catch (error: unknown) {
      if (!controller.signal.aborted) {
        setError(error instanceof Error ? error.message : 'Unable to load jobs.');
      }
    } finally {
      if (!controller.signal.aborted) setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    // Never display one token's tenant data after the token changes.
    requestRef.current?.abort();
    setJobs([]);
    setError(null);
    setIsLoading(false);
    return () => requestRef.current?.abort();
  }, [token]);

  return { jobs, isLoading, error, refresh, setError };
}
