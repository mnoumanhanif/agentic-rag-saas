"""Tests for resilience utilities (circuit breaker, retry, fallback)."""

import time

import pytest

from rag_system.utils.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    retry_with_backoff,
    with_fallback,
)


class TestCircuitBreaker:
    """Tests for the circuit breaker pattern."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    def test_stays_closed_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_success_resets_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_decorator_passes_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)

        @cb
        def succeed():
            return 42

        assert succeed() == 42
        assert cb.state == CircuitState.CLOSED

    def test_decorator_raises_when_open(self):
        cb = CircuitBreaker(failure_threshold=1)

        @cb
        def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            fail()

        # Circuit is now open
        with pytest.raises(CircuitOpenError):
            fail()


class TestRetryWithBackoff:
    """Tests for retry with exponential backoff."""

    def test_succeeds_first_try(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_retries_on_failure(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        assert fail_twice() == "ok"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            always_fail()

    def test_only_catches_specified_exceptions(self):
        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        def raise_type_error():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            raise_type_error()


class TestWithFallback:
    """Tests for graceful fallback decorator."""

    def test_returns_result_on_success(self):
        @with_fallback(fallback_value="default")
        def succeed():
            return "real"

        assert succeed() == "real"

    def test_returns_fallback_on_failure(self):
        @with_fallback(fallback_value="default")
        def fail():
            raise ValueError("boom")

        assert fail() == "default"

    def test_only_catches_specified_exceptions(self):
        @with_fallback(fallback_value="default", exceptions=(ValueError,))
        def raise_type_error():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            raise_type_error()

    def test_fallback_none(self):
        @with_fallback(fallback_value=None)
        def fail():
            raise RuntimeError("boom")

        assert fail() is None
