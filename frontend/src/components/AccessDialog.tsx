import { useEffect, useState, type FormEvent } from 'react';
import { Button, Dialog, Field, Input } from './ui';

interface Props {
  token: string;
  authenticated?: boolean;
  onChange: (token: string) => void;
  onClose: () => void;
  onConnected: () => void;
  onDisconnected: () => void;
}

interface SetupStatus {
  registration_available: boolean;
  account_exists: boolean;
  bootstrap_configured: boolean;
}

async function errorMessage(response: Response, registering: boolean): Promise<string> {
  let detail = '';
  try {
    const body = await response.json() as { detail?: string };
    if (typeof body.detail === 'string') detail = body.detail;
  } catch { /* Preserve a useful generic message when the response isn't JSON. */ }

  if (response.status === 401) return 'Incorrect email or password.';
  if (response.status === 429) return 'Too many attempts. Please try again in 15 minutes.';
  if (response.status === 403) {
    if (detail === 'Invalid request origin') return 'Browser origin rejected by the server. Rebuild the frontend proxy and try again.';
    if (detail === 'Bootstrap email is not configured on the backend') return 'Set ATLAS_BOOTSTRAP_EMAIL in .env and recreate the backend.';
    if (detail === 'Email does not match the configured bootstrap email') return 'Use the exact email configured in ATLAS_BOOTSTRAP_EMAIL.';
    if (detail === 'Initial account already registered') return 'An account already exists. Switch to Sign in.';
    if (detail === 'CSRF token required') return 'Session security check failed. Refresh the page and try again.';
    return registering ? 'Registration was denied. Check the bootstrap configuration.' : 'Access denied. Please check your account.';
  }
  if (response.status === 422) return 'Check your email and use a password of at least 12 characters.';
  if (response.status >= 500) return 'The authentication service is unavailable. Check the backend logs.';
  return 'Authentication failed (HTTP ' + response.status + ').';
}

export function AccessDialog({ authenticated = false, onChange, onClose, onConnected, onDisconnected }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [register, setRegister] = useState(false);
  const [setup, setSetup] = useState<SetupStatus | null>(null);
  const [setupLoading, setSetupLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/auth/setup', { credentials: 'same-origin', signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Unable to check account setup.');
        return response.json() as Promise<SetupStatus>;
      })
      .then(status => { setSetup(status); setRegister(status.registration_available); })
      .catch(() => { if (!controller.signal.aborted) setNotice('Could not check account setup. Verify the backend is running.'); })
      .finally(() => { if (!controller.signal.aborted) setSetupLoading(false); });
    return () => controller.abort();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/auth/' + (register ? 'register' : 'login'), {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      if (!response.ok) throw new Error(await errorMessage(response, register));
      setPassword('');
      onChange('');
      onConnected();
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to sign in.');
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const csrf = document.cookie.match(/(?:^|; )atlas_csrf=([^;]*)/)?.[1];
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: csrf ? { 'X-CSRF-Token': decodeURIComponent(csrf) } : {},
      });
      if (!response.ok) throw new Error(await errorMessage(response, false));
      onChange('');
      onDisconnected();
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to sign out.');
    } finally {
      setBusy(false);
    }
  }

  const canRegister = setup?.registration_available ?? false;
  return <Dialog.Root onBackdropClick={onClose}>
    <Dialog.Content labelledBy="access-title" className="auth-dialog">
      <div className="dialog-heading">
        <div className="auth-brand"><span className="auth-brand-mark">A<span>·</span></span><span>ATLAS <small>AI PLATFORM</small></span></div>
        <Button variant="unstyled" type="button" className="icon-button" aria-label="Close" onClick={onClose}>×</Button>
      </div>
      <div className="auth-heading">
        <span className="eyebrow">SECURE WORKSPACE ACCESS</span>
        <h2 id="access-title">{register ? 'Create your workspace account' : 'Welcome back'}</h2>
        <p className="muted">{register
          ? 'Create the first local account with the email configured for ATLAS.'
          : 'Sign in with your ATLAS credentials to continue.'}</p>
      </div>
      {setupLoading && <p className="auth-hint">Checking workspace configuration…</p>}
      {!setupLoading && !setup?.bootstrap_configured && <p className="auth-hint" role="status">
        First-time registration requires ATLAS_BOOTSTRAP_EMAIL in the backend environment.
      </p>}
      {notice && <p className="auth-hint" role="status">{notice}</p>}
      <form className="auth-form" onSubmit={submit}>
        <Field.Root id="access-email">
          <Field.Label>Email address</Field.Label>
          <Input type="email" autoComplete="username" required maxLength={254}
            placeholder="you@example.com" value={email}
            onChange={event => setEmail(event.target.value)} />
        </Field.Root>
        <Field.Root id="access-password">
          <Field.Label>Password</Field.Label>
          <div className="auth-password">
            <Input type={showPassword ? 'text' : 'password'} autoComplete={register ? 'new-password' : 'current-password'}
              minLength={12} required maxLength={256} placeholder="Enter your password" value={password}
              onChange={event => setPassword(event.target.value)} />
            <Button variant="unstyled" type="button" className="auth-reveal"
              aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>
              {showPassword ? 'Hide' : 'Show'}
            </Button>
          </div>
        </Field.Root>
        {register && <p className="auth-hint">Use at least 12 characters. This is a new ATLAS password, not your email password.</p>}
        {error && <p className="error-message auth-error" role="alert">{error}</p>}
        <Button type="submit" className="auth-submit" disabled={busy || setupLoading}>
          {busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'} <span aria-hidden="true">↗</span>
        </Button>
      </form>
      <div className="auth-footer">
        {canRegister && <p>{register ? 'Already have an account?' : 'First time here?'} <Button variant="unstyled" className="auth-link" type="button"
          onClick={() => { setRegister(!register); setError(''); }}>
          {register ? 'Sign in' : 'Create account'}</Button></p>}
        {!canRegister && setup?.account_exists && <p className="auth-hint">The initial account has already been created.</p>}
        {authenticated && <Button variant="unstyled" className="auth-signout" type="button" disabled={busy}
          onClick={() => void logout()}>Sign out of this browser</Button>}
      </div>
    </Dialog.Content>
  </Dialog.Root>;
}
