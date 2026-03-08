"""Pydantic models for API request/response validation."""

import html
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def _sanitize_text(text: str) -> str:
    """Sanitize user-supplied text.

    Strips control characters, escapes HTML entities, and normalises
    whitespace to prevent XSS and other injection attacks.
    """
    # Remove null bytes and non-printable control chars (keep \n, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Escape HTML entities
    text = html.escape(text, quote=True)
    return text.strip()


class QueryRequest(BaseModel):
    """Request model for querying the RAG system."""

    query: str = Field(..., min_length=1, max_length=5000, description="User query")
    chat_history: List[Dict] = Field(
        default_factory=list, description="Previous conversation turns"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and sanitize query input."""
        v = _sanitize_text(v)
        if not v:
            raise ValueError("Query cannot be empty")
        return v

    @field_validator("chat_history")
    @classmethod
    def validate_chat_history(cls, v: List[Dict]) -> List[Dict]:
        """Validate chat history format and sanitize content."""
        for msg in v:
            if "role" not in msg or "content" not in msg:
                raise ValueError(
                    "Each message must have 'role' and 'content' keys"
                )
            if msg["role"] not in ("user", "assistant"):
                raise ValueError("Role must be 'user' or 'assistant'")
            # Sanitize chat history content
            msg["content"] = _sanitize_text(str(msg["content"]))
        return v


class QueryResponse(BaseModel):
    """Response model for RAG queries."""

    answer: str = Field(..., description="Generated answer")
    sources: List[Dict] = Field(
        default_factory=list, description="Source documents used"
    )
    query_analysis: Optional[Dict] = Field(
        None, description="Query analysis results"
    )
    reflection: Optional[Dict] = Field(
        None, description="Answer reflection results"
    )
    steps: List[str] = Field(
        default_factory=list, description="Pipeline execution steps"
    )


class UploadResponse(BaseModel):
    """Response model for file uploads."""

    message: str
    files_processed: List[str]
    job_id: Optional[str] = Field(None, description="Background job ID for async tracking")


class JobStatusResponse(BaseModel):
    """Response model for background job status."""

    job_id: str
    status: str
    message: str = ""
    files: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    llm_available: bool
    vector_store_loaded: bool


class EvaluationRequest(BaseModel):
    """Request model for evaluation."""

    test_cases: List[Dict] = Field(
        ..., min_length=1, description="Test cases for evaluation"
    )


class EvaluationResponse(BaseModel):
    """Response model for evaluation results."""

    avg_faithfulness: float
    avg_context_relevance: float
    avg_answer_correctness: float
    avg_retrieval_recall: float
    avg_overall_score: float
    num_cases: int
