import { useState, type FormEvent } from 'react';
import type { JobType } from '../types/jobs';

interface Props {
  disabled: boolean;
  isSubmitting: boolean;
  onSubmit: (type: JobType, prompt: string, reference: string) => Promise<void>;
}
export function JobForm({ disabled, isSubmitting, onSubmit }: Props) {
  const [type, setType] = useState<JobType>('inference');
  const [prompt, setPrompt] = useState('');
  const [reference, setReference] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!prompt.trim() || disabled || isSubmitting) return;
    await onSubmit(type, prompt.trim(), reference.trim());
    setPrompt('');
    setReference('');
  }
  return <section aria-labelledby="create-heading">
    <h2 id="create-heading">Submit a job</h2>
    <form onSubmit={submit}>
      <label htmlFor="job-type">Job type</label>
      <select id="job-type" value={type} onChange={event => setType(event.target.value as JobType)}>
        <option value="inference">Inference demo</option>
        <option value="rag">Document question (RAG)</option>
      </select>
      <label htmlFor="job-prompt">{type === 'rag' ? 'Question' : 'Prompt'}</label>
      <textarea id="job-prompt" value={prompt} maxLength={type === 'rag' ? 2000 : 8000}
        onChange={event => setPrompt(event.target.value)}
        placeholder={type === 'rag' ? 'Ask a question about indexed documents' : 'Enter a prompt'} />
      {type === 'rag' && <>
        <label htmlFor="reference-answer">Reference answer (optional — enables evaluation)</label>
        <textarea id="reference-answer" value={reference} maxLength={16000}
          onChange={event => setReference(event.target.value)}
          placeholder="Expected answer for quality evaluation" />
      </>}
      <button type="submit" disabled={disabled || isSubmitting || !prompt.trim()}>
        {isSubmitting ? 'Submitting…' : 'Submit job'}
      </button>
    </form>
  </section>;
}
