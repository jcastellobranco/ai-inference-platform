import { useRef, useState, type FormEvent } from 'react';
import { Button, Field, Input, Textarea } from '../components/ui';
import { EmptyState } from '../components/EmptyState';
import { SectionHeader } from '../components/SectionHeader';
import { knowledgeApi } from '../lib/knowledgeApi';
import type { KnowledgeDocument } from '../types/knowledge';

interface Props {
  token: string; connected: boolean; documents: KnowledgeDocument[];
  loading: boolean; busy: boolean; error: string | null;
  mutate: (action: () => Promise<unknown>) => Promise<boolean>;
  refresh: () => Promise<void>; openAccess: () => void;
}
export function DocumentsPage({ token, connected, documents, loading, busy, error, mutate, refresh, openAccess }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<'pdf' | 'text'>('pdf');
  const [source, setSource] = useState('');
  const [content, setContent] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);

  function chooseFile(selected?: File) {
    setNotice('');
    if (!selected) return;
    if (selected.type !== 'application/pdf' && !selected.name.toLowerCase().endsWith('.pdf')) {
      setNotice('Please choose a PDF document.');
      return;
    }
    if (selected.size > 10 * 1024 * 1024) {
      setNotice('PDF exceeds the 10 MiB upload limit.');
      return;
    }
    setFile(selected);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!connected || busy) return;
    const ok = mode === 'pdf'
      ? file && await mutate(() => knowledgeApi.uploadPdf(token, file))
      : await mutate(() => knowledgeApi.ingestText(token, source.trim(), content.trim()));
    if (ok) {
      setFile(null); setSource(''); setContent('');
      if (fileRef.current) fileRef.current.value = '';
      setNotice('Document indexed successfully and ready for retrieval.');
    }
  }
  async function remove(item: KnowledgeDocument) {
    if (!window.confirm(`Delete "${item.source}" and all indexed chunks? This cannot be undone.`)) return;
    setDeleting(item.document_id);
    const ok = await mutate(() => knowledgeApi.remove(token, item.document_id));
    if (ok) setNotice(`${item.source} removed from the index.`);
    setDeleting(null);
  }
  return <>
    <SectionHeader eyebrow="KNOWLEDGE MANAGEMENT" title="Knowledge base"
      description="Turn your documents into searchable context. Each document is chunked, embedded and stored in PostgreSQL with pgvector."
      action={<button className="button-secondary" disabled={!connected || loading} onClick={() => void refresh()}>↻ Refresh library</button>} />
    <div className="document-layout">
      <section className="panel upload-panel">
        <div className="panel-topline"><span className="eyebrow">INGESTION</span><span className="step-chip">01 / INDEX</span></div>
        <h3>Add to your knowledge</h3>
        <p className="muted">Upload a PDF or paste plain text. Content is sent to the authenticated backend, never directly to the private RAG service.</p>
        <div className="mode-switch" role="group" aria-label="Document input">
          <button type="button" className={mode === 'pdf' ? 'selected' : ''} onClick={() => setMode('pdf')}>▤ PDF upload</button>
          <button type="button" className={mode === 'text' ? 'selected' : ''} onClick={() => setMode('text')}>≡ Plain text</button>
        </div>
        <form onSubmit={event => void submit(event)}>
          {mode === 'pdf' ? <>
            <input ref={fileRef} className="sr-only" id="pdf-file" type="file" accept=".pdf,application/pdf"
              onChange={event => chooseFile(event.target.files?.[0])} />
            <button type="button" className="dropzone" onClick={() => fileRef.current?.click()}
              onDragOver={event => event.preventDefault()}
              onDrop={event => { event.preventDefault(); chooseFile(event.dataTransfer.files[0]); }}>
              <span className="dropzone-symbol">⇧</span>
              <strong>{file ? file.name : 'Choose a file or drop it here'}</strong>
              <small>{file ? `${(file.size / 1024).toFixed(1)} KB · Ready to upload` : 'PDF only · Up to 10 MiB · Max 100 pages'}</small>
            </button>
          </> : <>
            <Field.Root id="source-name"><Field.Label>Source label</Field.Label>
            <Input value={source} maxLength={256} placeholder="architecture-notes.md"
              onChange={event => setSource(event.target.value)} required /></Field.Root>
            <Field.Root id="document-content"><Field.Label>Document content</Field.Label>
            <Textarea rows={8} maxLength={200000} value={content}
              placeholder="Paste the content you want to make searchable..."
              onChange={event => setContent(event.target.value)} required /></Field.Root>
            <div className="character-count">{content.length.toLocaleString()} / 200,000 characters</div>
          </>}
          <Button type="submit" className="wide-button" disabled={!connected || busy || (mode === 'pdf' ? !file : !source.trim() || !content.trim())}>
            {busy ? 'Indexing document…' : 'Index document'} <span>↗</span>
          </Button>
        </form>
        {!connected && <p className="inline-hint">Connect your JWT to index documents. <button onClick={openAccess}>Connect now →</button></p>}
        {notice && <p className="notice" role="status">{notice}</p>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>
      <section className="panel library-panel">
        <div className="panel-topline"><span className="eyebrow">YOUR LIBRARY</span><span className="count-chip">{documents.length} documents</span></div>
        <h3>Indexed sources</h3>
        <p className="muted">Document catalogue is persisted in the RAG database and isolated by tenant.</p>
        {loading ? <p className="loading-line">Loading documents…</p> :
          !connected ? <EmptyState icon="◇" title="Workspace disconnected" description="Connect to view your indexed sources." /> :
          documents.length === 0 ? <EmptyState icon="▤" title="Your library is empty" description="Index your first source to start exploring semantic search." /> :
          <div className="document-list">{documents.map(item =>
            <div key={item.document_id} className="document-row">
              <div className="file-symbol">{item.source.toLowerCase().endsWith('.pdf') ? 'PDF' : 'TXT'}</div>
              <div className="file-info"><strong title={item.source}>{item.source}</strong>
                <small>{item.chunks} chunks · {new Date(item.created_at).toLocaleDateString()}</small></div>
              <button type="button" className="delete-button" aria-label={`Delete ${item.source}`}
                title="Remove document" disabled={busy || deleting === item.document_id}
                onClick={() => void remove(item)}>×</button>
            </div>)}</div>}
        <div className="library-footer"><span>◈</span><p>Embeddings generated by sentence-transformers and stored in pgvector. Deleting a source removes its indexed chunks.</p></div>
      </section>
    </div>
  </>;
}
