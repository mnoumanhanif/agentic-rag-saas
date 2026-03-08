# =============================================================================
# Gunicorn configuration for production deployment
# =============================================================================
# Usage:
#   gunicorn -c gunicorn.conf.py "rag_system.api.server:get_app()"
# =============================================================================

import multiprocessing
import os

# ---------------------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------------------
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# ---------------------------------------------------------------------------
# Worker processes
# ---------------------------------------------------------------------------
# Recommended: 2-4 x $(NUM_CORES) for I/O-bound apps.
# Default to 2 workers; override via GUNICORN_WORKERS.
workers = int(os.getenv("GUNICORN_WORKERS", min(2, multiprocessing.cpu_count() + 1)))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # Restart workers after N requests to prevent memory leaks
max_requests_jitter = 50

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
timeout = 120  # LLM inference can be slow
graceful_timeout = 30
keepalive = 5

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# ---------------------------------------------------------------------------
# Process naming
# ---------------------------------------------------------------------------
proc_name = "rag-system"

# ---------------------------------------------------------------------------
# Pre-loading
# ---------------------------------------------------------------------------
# Pre-load the application to share memory between workers (copy-on-write).
# This significantly reduces memory usage when running multiple workers.
preload_app = True
