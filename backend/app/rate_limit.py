"""Optional Redis-backed authenticated request quota.

Disabled unless ATLAS_RATE_LIMIT_ENABLED=true. Fail closed on Redis outages.
Uses a fixed 60-second window; no client-provided tenant keys.
"""
import hashlib
import os
import redis
from fastapi import HTTPException

def _redis_connection():
    import redis
    host = os.getenv("ATLAS_REDIS_HOST", "")
    secret_file = os.getenv("ATLAS_REDIS_PASSWORD_FILE", "")
    if host and secret_file:
        with open(secret_file, encoding="utf-8") as handle:
            password = handle.read().strip()
        if len(password) < 32:
            raise ValueError("Redis secret must be at least 32 characters")
        return redis.Redis(host=host, port=6379, db=0, password=password,
                           socket_connect_timeout=1, socket_timeout=1)
    url = os.getenv("ATLAS_REDIS_URL", "")
    return redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)

_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return count
"""

def enforce_rate_limit(tenant: str, subject: str) -> None:
    if os.getenv("ATLAS_RATE_LIMIT_ENABLED", "false").lower() != "true":
        return
    if not os.getenv("ATLAS_REDIS_HOST") and not os.getenv("ATLAS_REDIS_URL"):
        raise HTTPException(503, "Rate limiter unavailable")
    try:
        limit = int(os.getenv("ATLAS_RATE_LIMIT_PER_MINUTE", "120"))
        if not 1 <= limit <= 10000:
            raise ValueError("Invalid rate limit")
        client = _redis_connection()
        digest = hashlib.sha256((tenant + "\x00" + subject).encode()).hexdigest()
        count = client.eval(_SCRIPT, 1, "atlas:quota:" + digest, 60)
    except (ValueError, OSError, redis.RedisError):
        raise HTTPException(503, "Rate limiter unavailable")
    if count > limit:
        raise HTTPException(429, "Request rate limit exceeded", headers={"Retry-After": "60"})
