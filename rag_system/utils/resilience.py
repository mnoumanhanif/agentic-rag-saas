"""Resilience utilities: circuit breaker, retry, and graceful degradation.

Provides production-grade error handling patterns for the RAG system.
"""

import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing — reject calls immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Simple circuit breaker for external service calls.

    Tracks consecutive failures and *opens* the circuit when
    ``failure_threshold`` is reached.  While open, calls are rejected
    immediately for ``recovery_timeout`` seconds.  After that, a single
    probe call is allowed (half-open state).

    Usage::

        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        @breaker
        def call_llm(prompt):
            ...
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "circuit",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("[%s] Circuit half-open — allowing probe request", self.name)
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        if self._state != CircuitState.CLOSED:
            logger.info("[%s] Circuit closed — service recovered", self.name)
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "[%s] Circuit opened — %d consecutive failures",
                self.name,
                self._failure_count,
            )

    def __call__(self, func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is open — service unavailable"
                )
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception:
                self.record_failure()
                raise

        return wrapper  # type: ignore[return-value]


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is in the open state."""


# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        exceptions: Tuple of exception types to catch and retry.

    Returns:
        Decorated function.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            "Retry %d/%d for %s after %.1fs: %s",
                            attempt + 1,
                            max_retries,
                            func.__name__,
                            delay,
                            exc,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Graceful fallback
# ---------------------------------------------------------------------------


def with_fallback(fallback_value: Any, exceptions: tuple = (Exception,)) -> Callable[[F], F]:
    """Decorator: return a fallback value instead of raising.

    Useful for non-critical operations where a degraded response is
    acceptable (e.g. reflection scoring, optional metadata).

    Args:
        fallback_value: Value to return when the function fails.
        exceptions: Exception types to catch.

    Returns:
        Decorated function.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exceptions as exc:
                logger.warning(
                    "Fallback triggered for %s: %s", func.__name__, exc
                )
                return fallback_value

        return wrapper  # type: ignore[return-value]

    return decorator
