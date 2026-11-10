"""Optional Redis-backed authenticated request quota.

Disabled unless ATLAS_RATE_LIMIT_ENABLED=true. Fail closed on Redis outages.
Uses a fixed 60-second window; no client-provided tenant keys.
"""
import hashlib
import os
import redis
from fastapi import HTTPException

_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""

def enforce_rate_limit(tenant: str, subject: str) -> None:
    if os.getenv("ATLAS_RATE_LIMIT_ENABLED", "false").lower() != "true":
        return
    url = os.getenv("ATLAS_REDIS_URL", "")
    if not url:
        raise HTTPException(503, "Rate limiter unavailable")
    try:
        limit = int(os.getenv("ATLAS_RATE_LIMIT_PER_MINUTE", "120"))
        if not 1 <= limit <= 10000:
            raise ValueError("Invalid rate limit")
        client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        digest = hashlib.sha256((tenant + "\x00" + subject).encode()).hexdigest()
        count = client.eval(_SCRIPT, 1, "atlas:quota:" + digest, 60)
    except (ValueError, redis.RedisError):
        raise HTTPException(503, "Rate limiter unavailable")
    if count > limit:
        raise HTTPException(429, "Request rate limit exceeded", headers={"Retry-After": "60"})
