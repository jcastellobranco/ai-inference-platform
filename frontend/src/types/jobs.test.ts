import { describe, expect, it } from 'vitest';
import { parseRagResult } from './jobs';

describe('parseRagResult', () => {
  it('parses an extractive answer with citations', () => {
    const result = parseRagResult(JSON.stringify({
      mode: 'extractive_first_chunk',
      answer: 'Pods run on nodes',
      citations: [{ source: 'manual.md', chunk_id: 'c1' }],
    }));
    expect(result?.answer).toBe('Pods run on nodes');
    expect(result?.citations[0].source).toBe('manual.md');
  });

  it('handles plain text, missing or malformed results gracefully', () => {
    expect(parseRagResult(null)).toBeNull();
    expect(parseRagResult('PENDING')).toBeNull();
    expect(parseRagResult('{"answer":"missing citation data"}')).toBeNull();
  });
});
