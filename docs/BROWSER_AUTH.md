# Browser login (local-first)

ATLAS now supports email/password sign-in without pasting a JWT into the React UI.

## Initial account

Set ATLAS_BOOTSTRAP_EMAIL in the root .env to the email address authorized to create the first account. This is an **allowlist**, not a default password. Choose a strong password (12+ characters) when registering in the browser.

    printf '\nATLAS_BOOTSTRAP_EMAIL=you@example.com\n' >> .env
    make config-redis
    make up-redis

Visit http://localhost:8080, choose Sign in -> First time? Create account, and register using the configured email. Registration closes automatically after the first account exists. The account is assigned to the first seeded local tenant; it does not grant access to other tenants.

For HTTPS deployments, set COOKIE_SECURE=true and ensure trusted reverse-proxy headers and HTTPS are configured. HTTP cookies are permitted **only** for the local development environment. Do not expose this demo directly on the internet.

## Security model

- Argon2id password hashes stored in PostgreSQL; never store plaintext passwords.
- Random opaque 12-hour sessions stored as SHA-256 digests; session cookie is HttpOnly, SameSite=Lax and Secure under HTTPS.
- A separate CSRF cookie and matching header are required on mutating session-authenticated API requests.
- Logout revokes the PostgreSQL session.
- Login/register attempts are throttled by remote IP and email.
- API principal resolves the tenant from the authenticated account; job RLS remains enforced in PostgreSQL.
- Existing JWT Bearer integration remains for scripts and service-to-service workflows.

## Limitations

This is a **single-account bootstrap** for local portfolio demonstration, not open public sign-up or a full identity provider. No password reset, MFA, email verification, administrative invitations, OIDC/JWKS, or account recovery are implemented. There is no session rotation after login and no central identity provider. HTTPS, trusted proxies, monitoring and independent security review are required before internet exposure.

## Troubleshooting login on localhost:8080

If you see **Invalid request origin**, rebuild the frontend Nginx image. The reverse proxy must preserve the browser's Host **including port 8080**; a proxy that forwards only `localhost` will reject requests originating from `http://localhost:8080`.

If registration is unavailable, visit `http://localhost:8080/api/auth/setup` to inspect the safe bootstrap status. `bootstrap_configured=false` means the backend container has not received `ATLAS_BOOTSTRAP_EMAIL`. `account_exists=true` means the first account already exists; use **Sign in**, not **Create account**.

Check the effective backend environment without printing secrets:

    docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml -f docker-compose.agents.yml -f docker-compose.redis.yml exec backend python -c 'import os; print("bootstrap configured:", bool(os.getenv("ATLAS_BOOTSTRAP_EMAIL")))'

Apply updates from the root repository directory:

    git switch main
    git pull --ff-only origin main
    make up-redis

**Do not run `docker compose down -v`** to troubleshoot login: it destroys the PostgreSQL volume containing your account and jobs. If the issue persists, inspect backend and migrate logs using the same Compose overlay flags as above.
