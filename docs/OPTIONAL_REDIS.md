# Optional Redis cache and distributed API quotas

This is an **optional overlay** for the full ATLAS stack, including the agent service. It does not change the PostgreSQL durable queue.

Prerequisites: sibling checkouts of RAG, Evaluation, Multi-Agent and MCP, plus the matching agent branch `feat/agent-guardrails-cache-observability` with the Redis client installed.

1. Copy `.env.example` to `.env`, and set unique random values for `ATLAS_REDIS_PASSWORD` and `ATLAS_CACHE_HMAC_KEY` (minimum 32 characters for the HMAC key). Never commit the .env.
2. Start:

```bash
docker compose -f docker-compose.fullstack.yml -f docker-compose.integrated.yml \
  -f docker-compose.agents.yml -f docker-compose.redis.yml up -d --build
```

Redis is internal-only (no published host port), password-protected, with a 128 MB maxmemory limit and LRU eviction. No AOF or RDB persistence: **do not use it for durable jobs or audit events**.

- Agent planner: HMAC-SHA256 cache keys include tenant, model, prompt and policy version; default 120-second TTL, opt-in with the overlay. Only plans are cached; tools execute on each request with fresh authorization.
- Backend: after validating JWT, a Redis Lua script enforces a per-tenant/per-subject fixed-window quota, default 120 authenticated requests per minute. 429 when exceeded, 503 when Redis is unavailable and quota enforcement is enabled (fail closed). Health endpoints remain accessible.
- The cache may return stale plans until TTL expires if policies change. Rotate `ATLAS_CACHE_HMAC_KEY` or bump policy version on deployment.
- Redis failure does not prevent agent planning (cache miss), but API rate limiting fails closed. This is intentional and should be included in operational readiness testing.
- This is not token-cost accounting, distributed tracing, a persistent queue or a production Redis HA setup.

To disable Redis, omit the overlay and redeploy. The default API quotas and agent planner cache remain disabled.
