import { useState, type FormEvent } from 'react';
import { Button, Dialog, Field, Textarea } from './ui';
interface Props { token: string; onChange: (token: string) => void; onClose: () => void; onConnected: () => void }
export function AccessDialog({ token, onChange, onClose, onConnected }: Props) {
  const [draft, setDraft] = useState(token);
  function submit(event: FormEvent) {
    event.preventDefault();
    onChange(draft.trim());
    onClose();
    onConnected();
  }
  return <Dialog.Root onBackdropClick={onClose}>
    <Dialog.Content labelledBy="access-title">
      <div className="dialog-heading">
        <div className="dialog-symbol">◇</div>
        <Button variant="unstyled" type="button" className="icon-button" aria-label="Close" onClick={onClose}>×</Button>
      </div>
      <span className="eyebrow">DEVELOPMENT CONNECTION</span>
      <h2 id="access-title">Connect your workspace</h2>
      <p className="muted">Paste a short-lived developer JWT. Credentials stay in tab memory and are never saved to disk.</p>
      <form onSubmit={submit}>
        <Field.Root id="access-jwt"><Field.Label>JWT access token</Field.Label>
        <Textarea className="jwt-input" spellCheck={false} autoComplete="off"
          value={draft} onChange={event => setDraft(event.target.value)}
          placeholder="eyJhbGciOiJIUzI1NiIs..." rows={3} /></Field.Root>
        <div className="dialog-actions">
          <Button variant="unstyled" className="button-quiet" type="button" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={!draft.trim()}>
            Connect workspace <span>↗</span>
          </Button>
        </div>
      </form>
      {token && <Button variant="unstyled" className="disconnect" type="button"
        onClick={() => { onChange(''); onClose(); }}>Disconnect current session</Button>}
    </Dialog.Content>
  </Dialog.Root>;
}
