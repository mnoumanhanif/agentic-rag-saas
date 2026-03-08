"""Security middleware and utilities for the Agentic RAG system.

Provides:
- Prompt injection detection and sanitization
- API key authentication
- Security headers middleware
- Request ID tracing
"""

import logging
import re
import secrets
import time
from typing import Callable, Optional

from fastapi import HTTPException, Request, Response, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt injection protection
# ---------------------------------------------------------------------------

# Patterns that indicate prompt injection / jailbreak attempts
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?above\s+instructions",
        r"disregard\s+(all\s+)?previous",
        r"forget\s+(all\s+)?previous",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"act\s+as\s+(a|an)\s+",
        r"pretend\s+(to\s+be|you\s+are)",
        r"system\s*prompt",
        r"reveal\s+(your|the)\s+(system|initial)\s+prompt",
        r"what\s+(is|are)\s+your\s+(system|initial)\s+(prompt|instructions)",
        r"repeat\s+(your|the)\s+(system|initial)\s+prompt",
        r"output\s+(your|the)\s+(system|initial)\s+prompt",
        r"show\s+me\s+your\s+(system|initial)\s+prompt",
        r"\bDAN\b",
        r"do\s+anything\s+now",
        r"jailbreak",
        r"bypass\s+(the\s+)?(safety|filter|restriction)",
    ]
]


def detect_prompt_injection(text: str) -> bool:
    """Check if text contains known prompt injection patterns.

    Args:
        text: User input to check.

    Returns:
        True if a prompt injection pattern is detected.
    """
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


def sanitize_prompt(text: str) -> str:
    """Sanitize user input before sending to the LLM.

    Delegates to the shared ``_sanitize_text`` helper in models for
    control-character removal, then applies LLM-specific normalisation
    (collapsing excessive whitespace).

    Args:
        text: Raw user input.

    Returns:
        Sanitized text.
    """
    from rag_system.api.models import _sanitize_text

    text = _sanitize_text(text)
    # Collapse excessive whitespace (LLM-specific)
    text = re.sub(r" {4,}", "   ", text)
    # Limit consecutive newlines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(_api_key_header),
) -> Optional[str]:
    """Validate the API key from the request header.

    When ``REQUIRE_API_KEY`` is falsy (the default for development), all
    requests are allowed through.  In production, set ``API_KEYS`` in the
    environment to a comma-separated list of valid keys.

    Returns:
        The validated API key, or ``None`` when authentication is disabled.

    Raises:
        HTTPException: 401 when an invalid key is supplied.
    """
    import os

    require = os.getenv("REQUIRE_API_KEY", "").lower() in ("1", "true", "yes")
    if not require:
        return api_key  # auth disabled — let everything through

    valid_keys = {
        k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()
    }
    if not valid_keys:
        logger.warning("REQUIRE_API_KEY is set but API_KEYS is empty")
        return api_key

    if not api_key or api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


def generate_api_key() -> str:
    """Generate a cryptographically secure API key.

    Returns:
        A 32-byte URL-safe token.
    """
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response.

    Headers applied:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - Content-Security-Policy (API-appropriate)
    - Cache-Control for API responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'"
        )

        # Prevent caching of API responses that may contain sensitive data
        if request.url.path.startswith("/query") or request.url.path.startswith(
            "/upload"
        ):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )

        return response


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response.

    The ID is available in ``request.state.request_id`` for downstream
    handlers and is returned in the ``X-Request-ID`` response header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get(
            "X-Request-ID", secrets.token_hex(8)
        )
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# IP throttle middleware (stricter than the general rate limiter)
# ---------------------------------------------------------------------------


class IPThrottleMiddleware(BaseHTTPMiddleware):
    """Per-IP request throttle with sliding window.

    Designed to sit *before* the general rate limiter and catch abusive IPs
    early.  Returns 429 when the threshold is exceeded.
    """

    def __init__(
        self,
        app,
        max_requests: int = 120,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window_seconds

        bucket = self._buckets.get(client_ip, [])
        bucket = [t for t in bucket if t > cutoff]

        if len(bucket) >= self.max_requests:
            logger.warning("IP throttle exceeded for %s", client_ip)
            return Response(
                content="Too many requests. Please slow down.",
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )

        bucket.append(now)
        self._buckets[client_ip] = bucket
        return await call_next(request)
