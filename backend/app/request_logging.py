"""Small dependency-free request telemetry for the ATLAS API.

Does not log authorization headers, request bodies, query strings, or tenant IDs.
"""
import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("atlas.http")
from .telemetry import REQUESTS, LATENCY


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid4())
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            # Avoid raw URLs, which may contain customer identifiers.
            route = request.scope.get("route")
            route_pattern = getattr(route, "path", "unmatched")
            REQUESTS.labels(method=request.method, route=route_pattern, status=str(status)).inc()
            LATENCY.labels(method=request.method, route=route_pattern).observe(elapsed_ms / 1000)
            logger.info(
                "http_request method=%s route=%s status=%s duration_ms=%.2f request_id=%s",
                request.method, route_pattern, status, elapsed_ms, request_id,
            )
