import { useState, type FormEvent } from 'react';
import { Button, Dialog, Field } from './ui';

interface Props {
  token: string;
  onChange: (token: string) => void;
  onClose: () => void;
  onConnected: () => void;
  onDisconnected: () => void;
}

export function AccessDialog({ onChange, onClose, onConnected, onDisconnected }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/auth/' + (register ? 'register' : 'login'), {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) throw new Error(response.status === 401 ? 'Invalid email or password.' :
        response.status === 403 ? 'Registration is disabled or account already exists.' : 'Login failed (HTTP ' + response.status + ').');
      onChange(''); onConnected(); onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to sign in.');
    } finally { setBusy(false); }
  }
  async function logout() {
    const csrf = document.cookie.match(/(?:^|; )atlas_csrf=([^;]*)/)?.[1];
    await fetch('/api/auth/logout', {
      method: 'POST', credentials: 'same-origin',
      headers: csrf ? { 'X-CSRF-Token': decodeURIComponent(csrf) } : {},
    });
    onChange(''); onDisconnected(); onClose();
  }
  return <Dialog.Root onBackdropClick={onClose}>
    <Dialog.Content labelledBy="access-title">
      <div className="dialog-heading">
        <div className="dialog-symbol">◇</div>
        <Button variant="unstyled" type="button" className="icon-button" aria-label="Close" onClick={onClose}>×</Button>
      </div>
      <span className="eyebrow">ATLAS ACCOUNT</span>
      <h2 id="access-title">{register ? 'Create your first account' : 'Sign in to your workspace'}</h2>
      <p className="muted">Use your account credentials. Your browser keeps a revocable session.</p>
      <form onSubmit={submit}>
        <Field.Root id="access-email"><Field.Label>Email</Field.Label>
          <input id="access-email" type="email" autoComplete="username" required value={email}
            onChange={event => setEmail(event.target.value)} /></Field.Root>
        <Field.Root id="access-password"><Field.Label>Password</Field.Label>
          <input id="access-password" type="password" autoComplete={register ? 'new-password' : 'current-password'}
            minLength={12} required value={password} onChange={event => setPassword(event.target.value)} /></Field.Root>
        {error && <p role="alert">{error}</p>}
        <div className="dialog-actions">
          <Button variant="unstyled" className="button-quiet" type="button" onClick={onClose}>Cancel</Button>
          <Button type="submit" disabled={busy}>{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}</Button>
        </div>
      </form>
      <Button variant="unstyled" type="button" onClick={() => { setRegister(!register); setError(''); }}>
        {register ? 'Already registered? Sign in' : 'First time? Create account'}
      </Button>
      <Button variant="unstyled" className="disconnect" type="button" onClick={() => void logout()}>
        Sign out of current session
      </Button>
    </Dialog.Content>
  </Dialog.Root>;

}
