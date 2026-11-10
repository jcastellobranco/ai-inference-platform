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
