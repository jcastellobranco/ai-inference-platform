import { Button, Field, Select, Textarea } from './ui';
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
      <Field.Root id="job-type"><Field.Label>Job type</Field.Label>
      <Select.Control value={type} onChange={event => setType(event.target.value as JobType)}>
        <Select.Option value="inference">Inference demo</Select.Option>
        <Select.Option value="rag">Document question (RAG)</Select.Option>
      </Select.Control></Field.Root>
      <Field.Root id="job-prompt"><Field.Label>{type === 'rag' ? 'Question' : 'Prompt'}</Field.Label>
      <Textarea value={prompt} maxLength={type === 'rag' ? 2000 : 8000}
        onChange={event => setPrompt(event.target.value)}
        placeholder={type === 'rag' ? 'Ask a question about indexed documents' : 'Enter a prompt'} /></Field.Root>
      {type === 'rag' && <>
        <Field.Root id="reference-answer"><Field.Label>Reference answer (optional — enables evaluation)</Field.Label>
        <Textarea value={reference} maxLength={16000}
          onChange={event => setReference(event.target.value)}
          placeholder="Expected answer for quality evaluation" /></Field.Root>
      </>}
      <Button type="submit" disabled={disabled || isSubmitting || !prompt.trim()}>
        {isSubmitting ? 'Submitting…' : 'Submit job'}
      </Button>
    </form>
  </section>;
}
