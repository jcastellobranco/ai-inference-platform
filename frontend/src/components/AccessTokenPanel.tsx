import { Button, Field, Input } from './ui';
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
    
    <div className="inline-fields">
      <Field.Root id="access-token"><Field.Label>JWT access token</Field.Label><Input type="password" autoComplete="off" spellCheck={false}
        value={token} onChange={event => onTokenChange(event.target.value)} placeholder="Paste a JWT" /></Field.Root>
      <Button type="button" onClick={onLoad} disabled={!token.trim() || isLoading}>
        {isLoading ? 'Loading…' : 'Load jobs'}
      </Button>
    </div>
  </section>;
}
