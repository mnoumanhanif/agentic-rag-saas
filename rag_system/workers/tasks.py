"""Background task processing for document ingestion.

Uses Redis + RQ for asynchronous processing of heavy operations:
- Document chunking
- Embedding generation
- Vector indexing

When Redis is not available, falls back to synchronous processing.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status of a background processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobInfo:
    """Information about a background job."""

    job_id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = ""
    files: List[str] = field(default_factory=list)
    created_at: float = 0.0
    completed_at: Optional[float] = None
    error: Optional[str] = None


# In-memory job store for when Redis is not available
_job_store: Dict[str, JobInfo] = {}


def get_job_info(job_id: str) -> Optional[JobInfo]:
    """Get job information by ID.

    First checks the in-memory store. If Redis + RQ is available,
    also checks the RQ job status.

    Args:
        job_id: The job identifier.

    Returns:
        JobInfo or None if not found.
    """
    # Check in-memory store first
    if job_id in _job_store:
        return _job_store[job_id]

    # Try RQ job status
    try:
        from redis import Redis
        from rq.job import Job

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        conn = Redis.from_url(redis_url)
        job = Job.fetch(job_id, connection=conn)

        info = JobInfo(
            job_id=job_id,
            created_at=job.enqueued_at.timestamp() if job.enqueued_at else 0,
        )

        if job.is_finished:
            info.status = JobStatus.COMPLETED
            info.message = job.result or "Completed"
            info.completed_at = job.ended_at.timestamp() if job.ended_at else time.time()
        elif job.is_failed:
            info.status = JobStatus.FAILED
            info.error = str(job.exc_info) if job.exc_info else "Unknown error"
        elif job.is_started:
            info.status = JobStatus.PROCESSING
        else:
            info.status = JobStatus.QUEUED

        return info
    except Exception:
        return None


def enqueue_ingestion(pdf_paths: List[str], pipeline=None) -> JobInfo:
    """Enqueue document ingestion as a background job.

    Attempts to use Redis + RQ for async processing. Falls back to
    synchronous processing if Redis is unavailable.

    Args:
        pdf_paths: Paths to PDF files to ingest.
        pipeline: The pipeline instance to use for ingestion.

    Returns:
        JobInfo with the job status.
    """
    job_id = f"ingest-{uuid.uuid4().hex[:12]}"

    # Try Redis + RQ first
    try:
        from redis import Redis
        from rq import Queue

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        conn = Redis.from_url(redis_url)
        conn.ping()  # Test connection

        queue = Queue(connection=conn)
        rq_job = queue.enqueue(
            _process_ingestion_task,
            pdf_paths,
            job_id=job_id,
            job_timeout=600,
        )

        info = JobInfo(
            job_id=rq_job.id,
            status=JobStatus.QUEUED,
            files=[os.path.basename(p) for p in pdf_paths],
            created_at=time.time(),
        )
        _job_store[rq_job.id] = info
        logger.info("Enqueued ingestion job %s with %d files", rq_job.id, len(pdf_paths))
        return info

    except Exception as e:
        logger.info("Redis not available (%s), using synchronous processing", e)

    # Fallback: synchronous processing
    info = JobInfo(
        job_id=job_id,
        status=JobStatus.PROCESSING,
        files=[os.path.basename(p) for p in pdf_paths],
        created_at=time.time(),
    )
    _job_store[job_id] = info

    try:
        if pipeline:
            message = pipeline.ingest_pdfs(pdf_paths)
            info.status = JobStatus.COMPLETED
            info.message = message
        else:
            info.status = JobStatus.FAILED
            info.error = "No pipeline available"
    except Exception as e:
        info.status = JobStatus.FAILED
        info.error = str(e)
        logger.error("Synchronous ingestion failed: %s", e)

    info.completed_at = time.time()
    return info


def _process_ingestion_task(pdf_paths: List[str]) -> str:
    """Background task for document ingestion.

    This function runs in an RQ worker process. It processes the
    documents and cleans up temporary files after completion.

    Args:
        pdf_paths: Paths to PDF files to ingest.

    Returns:
        Status message.
    """
    from rag_system.config.settings import get_settings
    from rag_system.pipelines.ingestion_pipeline import IngestionPipeline

    settings = get_settings()
    pipeline = IngestionPipeline(settings)

    try:
        return pipeline.ingest_pdfs(pdf_paths)
    finally:
        # Clean up temporary upload files
        for path in pdf_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    logger.warning("Failed to remove temp file: %s", path)
