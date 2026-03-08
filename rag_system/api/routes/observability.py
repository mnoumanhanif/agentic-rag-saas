"""Observability: Prometheus-compatible metrics endpoint and structured logging."""

import json
import logging
import threading
import time
from typing import Dict

from fastapi import APIRouter, Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"])

# ── In-process metrics counters ────────────────────────────────────────────
# Thread-safe counters using a lock for concurrent access.
# In production, swap with prometheus_client gauges/counters.

_lock = threading.Lock()

_metrics: Dict[str, float] = {
    "http_requests_total": 0,
    "http_errors_total": 0,
    "query_requests_total": 0,
    "query_latency_seconds_sum": 0.0,
    "query_latency_seconds_count": 0,
    "upload_requests_total": 0,
    "auth_login_total": 0,
    "auth_signup_total": 0,
    "active_users_gauge": 0,
}


def inc(name: str, amount: float = 1) -> None:
    """Increment a metric counter (thread-safe)."""
    with _lock:
        _metrics[name] = _metrics.get(name, 0) + amount


def observe_latency(seconds: float) -> None:
    """Record a query latency observation (thread-safe)."""
    with _lock:
        _metrics["query_latency_seconds_sum"] += seconds
        _metrics["query_latency_seconds_count"] += 1


def get_metrics() -> Dict[str, float]:
    """Return a snapshot of all metrics."""
    with _lock:
        return dict(_metrics)


@router.get("/metrics")
def prometheus_metrics():
    """Expose metrics in Prometheus text exposition format."""
    snapshot = get_metrics()
    lines = []
    for key, value in snapshot.items():
        # Convert to Prometheus format
        metric_name = f"rag_saas_{key}"
        if isinstance(value, float):
            lines.append(f"{metric_name} {value:.6f}")
        else:
            lines.append(f"{metric_name} {value}")
    return Response(content="\n".join(lines) + "\n", media_type="text/plain")


@router.get("/health/detailed")
def detailed_health():
    """Detailed health check with metrics summary."""
    snapshot = get_metrics()
    avg_latency = 0.0
    if snapshot["query_latency_seconds_count"] > 0:
        avg_latency = snapshot["query_latency_seconds_sum"] / snapshot["query_latency_seconds_count"]

    return {
        "status": "healthy",
        "metrics": {
            "total_requests": snapshot["http_requests_total"],
            "total_queries": snapshot["query_requests_total"],
            "avg_query_latency_ms": round(avg_latency * 1000, 2),
            "total_uploads": snapshot["upload_requests_total"],
            "error_count": snapshot["http_errors_total"],
        },
    }
