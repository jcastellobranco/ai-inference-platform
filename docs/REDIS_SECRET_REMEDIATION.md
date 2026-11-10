# Redis secret file (local Compose)

The GitGuardian alert on commit `3853a07` concerned variable interpolation in `docker-compose.redis.yml`. The old committed file contained **variable references**, not an actual password. This change removes password interpolation from Redis command arguments and connection URLs, replacing it with a local mounted Compose secret.

Create a password file before starting the Redis overlay:

```bash
mkdir -p .secrets
python -c "import secrets,pathlib; p=pathlib.Path('.secrets/redis_password'); p.write_text(secrets.token_urlsafe(48)); p.chmod(0o600)"
```

Do not commit the secret file. Keep `ATLAS_CACHE_HMAC_KEY` as a separate 32+ character secret in your untracked `.env`. The agent and backend read the mounted Redis password at runtime. Redis uses a temporary configuration file and has no host port.

**Limitations:** local Compose secrets are file mounts, not a production secrets manager. Redis config exists inside its ephemeral container filesystem; protect Docker host access. The previous GitGuardian finding may remain attached to the historical commit; if it is confirmed to be a variable-reference false positive, dismiss it with that explanation. If any real credential was ever committed, rotate it immediately.
