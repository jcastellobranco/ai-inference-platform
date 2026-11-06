interface Props {
  token: string;
  onTokenChange: (token: string) => void;
  onLoad: () => void;
  isLoading: boolean;
}
export function AccessTokenPanel({ token, onTokenChange, onLoad, isLoading }: Props) {
  return <section aria-labelledby="access-heading">
    <h2 id="access-heading">Development access</h2>
    <p>Enter a short-lived JWT for local development. The token stays in page memory and is never saved.</p>
    <label htmlFor="access-token">JWT access token</label>
    <div className="inline-fields">
      <input id="access-token" type="password" autoComplete="off" spellCheck={false}
        value={token} onChange={event => onTokenChange(event.target.value)} placeholder="Paste a JWT" />
      <button type="button" onClick={onLoad} disabled={!token.trim() || isLoading}>
        {isLoading ? 'Loading…' : 'Load jobs'}
      </button>
    </div>
  </section>;
}
