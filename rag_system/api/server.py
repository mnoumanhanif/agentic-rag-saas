"""FastAPI server for the Agentic RAG system."""

import asyncio
import logging
import os
import shutil
import time
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import rag_system
from rag_system.api.middleware import LoggingMiddleware, RateLimitMiddleware
from rag_system.api.models import (
    EvaluationRequest,
    EvaluationResponse,
    HealthResponse,
    JobStatusResponse,
    QueryRequest,
    QueryResponse,
    UploadResponse,
)
from rag_system.api.security import (
    IPThrottleMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    detect_prompt_injection,
    sanitize_prompt,
    verify_api_key,
)
from rag_system.config.settings import get_settings
from rag_system.evaluation.evaluator import RAGEvaluator
from rag_system.pipelines.agentic_rag_pipeline import AgenticRAGPipeline
from rag_system.workers.tasks import JobStatus, enqueue_ingestion, get_job_info

# SaaS modules
from rag_system.database.models import Base
from rag_system.database.engine import engine
from rag_system.api.routes import auth as auth_routes
from rag_system.api.routes import knowledge_bases as kb_routes
from rag_system.api.routes import conversations as conv_routes
from rag_system.api.routes import documents as doc_routes
from rag_system.api.routes import admin as admin_routes
from rag_system.api.routes import observability as obs_routes

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def create_app(pipeline: "AgenticRAGPipeline | None" = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        pipeline: Optional pre-created pipeline (useful for testing).

    Returns:
        Configured FastAPI app instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Agentic RAG SaaS Platform API",
        description="Production-ready Agentic RAG SaaS platform with multi-tenant knowledge bases, JWT auth, and analytics",
        version=rag_system.__version__,
        # Hide docs in production when API key is required
        docs_url="/docs" if not settings.security.require_api_key else None,
        redoc_url="/redoc" if not settings.security.require_api_key else None,
    )

    # --------------- Database initialisation --------------------------------
    Base.metadata.create_all(bind=engine)

    # --------------- Middleware stack (outermost → innermost) ---------------
    # 1. Security headers on every response
    if settings.security.enable_security_headers:
        app.add_middleware(SecurityHeadersMiddleware)

    # 2. Request ID tracing
    app.add_middleware(RequestIDMiddleware)

    # 3. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
    )

    # 4. IP throttle (broad limit)
    if settings.security.enable_ip_throttle:
        app.add_middleware(
            IPThrottleMiddleware,
            max_requests=settings.security.ip_throttle_max_requests,
            window_seconds=settings.security.ip_throttle_window_seconds,
        )

    # 5. Endpoint-aware rate limiter
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.api.rate_limit_requests,
        window_seconds=settings.api.rate_limit_window_seconds,
    )

    # 6. Request/response logging
    app.add_middleware(LoggingMiddleware)

    # --------------- SaaS route registration --------------------------------
    app.include_router(auth_routes.router)
    app.include_router(kb_routes.router)
    app.include_router(conv_routes.router)
    app.include_router(doc_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(admin_routes.analytics_router)
    app.include_router(obs_routes.router)

    # --------------- Pipeline initialisation --------------------------------
    if pipeline is None:
        pipeline = AgenticRAGPipeline(settings)
    evaluator = RAGEvaluator()

    # --------------- Public endpoints (no auth required) --------------------

    @app.get("/", response_model=dict)
    def read_root():
        """Root endpoint."""
        return {
            "message": "Welcome to the Agentic RAG System API",
            "version": rag_system.__version__,
            "docs": "/docs",
        }

    @app.get("/health", response_model=HealthResponse)
    def health_check():
        """System health check endpoint.

        Uses direct attribute access to avoid triggering lazy initialization
        of heavy resources (embedding models, vector stores) which could
        cause timeouts or OOM on resource-constrained deployments.
        """
        return HealthResponse(
            status="healthy",
            version=rag_system.__version__,
            llm_available=pipeline.llm is not None,
            vector_store_loaded=pipeline.ingestion.vector_store is not None,
        )

    # --------------- Protected endpoints (API key when enabled) -------------

    @app.post("/upload", response_model=UploadResponse)
    async def upload_files(
        files: List[UploadFile] = File(...),
        _api_key: Optional[str] = Depends(verify_api_key),
    ):
        """Upload and process PDF documents.

        Files are validated, saved, and then processed. When background
        workers are enabled, processing is offloaded to a Redis + RQ
        worker and the API returns immediately with a job ID.

        Args:
            files: PDF files to upload and process.

        Returns:
            Upload result with processing details and optional job ID.
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        max_size = settings.api.max_upload_size_mb * 1024 * 1024
        allowed_ext = settings.security.allowed_upload_extensions

        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        saved_paths: List[str] = []

        try:
            for file in files:
                if not file.filename:
                    continue

                # Validate file extension
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in allowed_ext:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Only {', '.join(allowed_ext)} files are supported. Got: {file.filename}",
                    )

                # Read content and validate size
                content = await file.read()
                if len(content) > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File {file.filename} exceeds the {settings.api.max_upload_size_mb}MB limit",
                    )

                # Validate PDF: check magic bytes and basic structure
                if not content[:5] == b"%PDF-":
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {file.filename} is not a valid PDF",
                    )
                # Verify PDF has a valid trailer (%%EOF marker)
                tail = content[-1024:] if len(content) > 1024 else content
                if b"%%EOF" not in tail:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {file.filename} appears to be a corrupted PDF",
                    )

                file_path = os.path.join(temp_dir, os.path.basename(file.filename))
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                saved_paths.append(file_path)

            # Try async processing via background worker
            if settings.worker.enabled:
                job_info = enqueue_ingestion(saved_paths, pipeline=pipeline)
                return UploadResponse(
                    message=f"Upload accepted. {len(saved_paths)} files queued for processing.",
                    files_processed=[f.filename for f in files if f.filename],
                    job_id=job_info.job_id,
                )

            # Synchronous processing (default)
            start_time = time.time()
            message = await asyncio.to_thread(pipeline.ingest_pdfs, saved_paths)
            duration = time.time() - start_time
            logger.info("Document ingestion completed in %.2fs", duration)

            return UploadResponse(
                message=message,
                files_processed=[f.filename for f in files if f.filename],
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Upload failed: %s", e)
            raise HTTPException(status_code=500, detail="Upload processing failed")
        finally:
            # Cleanup temp files (only if sync processing or failed)
            if not settings.worker.enabled:
                for path in saved_paths:
                    if os.path.exists(path):
                        os.remove(path)
                if os.path.exists(temp_dir):
                    try:
                        os.rmdir(temp_dir)
                    except OSError:
                        pass

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    async def get_job_status(
        job_id: str,
        _api_key: Optional[str] = Depends(verify_api_key),
    ):
        """Get the status of a background processing job.

        Args:
            job_id: The job identifier returned from upload.

        Returns:
            Current job status and details.
        """
        info = get_job_info(job_id)
        if info is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return JobStatusResponse(
            job_id=info.job_id,
            status=info.status.value,
            message=info.message,
            files=info.files,
            error=info.error,
        )

    @app.post("/query", response_model=QueryResponse)
    async def query_rag(
        request: QueryRequest,
        _api_key: Optional[str] = Depends(verify_api_key),
    ):
        """Query the RAG system with agentic processing.

        Args:
            request: Query request with question and optional chat history.

        Returns:
            Generated answer with sources and metadata.
        """
        try:
            query = request.query
            start_time = time.time()

            # Prompt injection detection
            if settings.security.enable_prompt_injection_detection:
                if detect_prompt_injection(query):
                    logger.warning("Prompt injection attempt detected: %s", query[:100])
                    raise HTTPException(
                        status_code=400,
                        detail="Your query contains patterns that are not allowed. Please rephrase your question.",
                    )

            # Sanitize prompt before sending to LLM
            query = sanitize_prompt(query)

            result = await asyncio.to_thread(
                pipeline.query, query, request.chat_history
            )

            duration = time.time() - start_time
            logger.info(
                "Query processed in %.2fs, steps=%d, sources=%d",
                duration,
                len(result.steps),
                len(result.sources),
            )

            return QueryResponse(
                answer=result.answer,
                sources=result.sources,
                query_analysis=result.query_analysis,
                reflection=result.reflection,
                steps=result.steps,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Query failed: %s", e)
            raise HTTPException(status_code=500, detail="Query processing failed")

    @app.post("/evaluate", response_model=EvaluationResponse)
    async def evaluate(
        request: EvaluationRequest,
        _api_key: Optional[str] = Depends(verify_api_key),
    ):
        """Evaluate RAG system quality with test cases.

        Args:
            request: Evaluation request with test cases.

        Returns:
            Evaluation results with aggregate metrics.
        """
        try:
            result = await asyncio.to_thread(evaluator.run_benchmark, request.test_cases)
            return EvaluationResponse(
                avg_faithfulness=result.avg_faithfulness,
                avg_context_relevance=result.avg_context_relevance,
                avg_answer_correctness=result.avg_answer_correctness,
                avg_retrieval_recall=result.avg_retrieval_recall,
                avg_overall_score=result.avg_overall_score,
                num_cases=len(result.results),
            )
        except Exception as e:
            logger.error("Evaluation failed: %s", e)
            raise HTTPException(status_code=500, detail="Evaluation processing failed")

    return app


def _get_app() -> FastAPI:
    """Get or create the global FastAPI app (for uvicorn)."""
    return create_app()


# Lazy app creation - only instantiated when actually needed by uvicorn
# Tests should use create_app(pipeline=mock) directly
app = None


def get_app() -> FastAPI:
    """Get the FastAPI app, creating it if needed."""
    global app
    if app is None:
        app = create_app()
    return app

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(get_app(), host=settings.api.host, port=settings.api.port)
