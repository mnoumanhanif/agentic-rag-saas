"""Middleware for the FastAPI server."""

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter middleware.

    Limits requests per client IP within a configurable time window.
    Applies stricter limits to mutation endpoints (POST/PUT/DELETE).
    """

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            HTTP response or 429 if rate limited.
        """
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < self.window_seconds
        ]

        # Stricter limit for mutation endpoints
        limit = self.max_requests
        if request.method in ("POST", "PUT", "DELETE"):
            limit = max(5, limit // 2)

        if len(self._requests[client_ip]) >= limit:
            logger.warning("Rate limit exceeded for %s on %s", client_ip, request.url.path)
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging middleware.

    Logs request details, response time, and includes request ID
    when available.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details and response time.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            HTTP response.
        """
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "-")
        client_ip = request.client.host if request.client else "unknown"

        logger.info(
            "[%s] %s %s from %s",
            request_id,
            request.method,
            request.url.path,
            client_ip,
        )

        response = await call_next(request)

        duration = time.time() - start_time
        logger.info(
            "[%s] %s %s -> %d (%.3fs)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response
