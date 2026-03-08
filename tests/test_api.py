"""Tests for the API server."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from rag_system.api.server import create_app
from rag_system.pipelines.agentic_rag_pipeline import PipelineResponse


@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline for testing."""
    pipeline = MagicMock()
    pipeline.llm = None
    pipeline.ingestion.vector_store = None
    pipeline.ingestion.get_vector_store.return_value = None
    pipeline.query.return_value = PipelineResponse(
        answer="Test answer",
        sources=[],
        steps=["test step"],
    )
    pipeline.ingest_pdfs.return_value = "Processed 1 file"
    return pipeline


@pytest.fixture
def client(mock_pipeline):
    """Create a test client with mocked pipeline."""
    app = create_app(pipeline=mock_pipeline)
    return TestClient(app)


class TestAPIEndpoints:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Agentic RAG" in data["message"]

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "llm_available" in data
        assert "vector_store_loaded" in data

    def test_query_empty(self, client):
        response = client.post("/query", json={"query": ""})
        assert response.status_code == 422  # Validation error

    def test_query_without_docs(self, client):
        response = client.post("/query", json={"query": "What is AI?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    def test_upload_no_files(self, client):
        response = client.post("/upload")
        assert response.status_code == 422

    def test_evaluate(self, client):
        test_cases = [
            {
                "query": "What is AI?",
                "answer": "AI is artificial intelligence",
                "context": "Artificial intelligence is a field",
            }
        ]
        response = client.post("/evaluate", json={"test_cases": test_cases})
        assert response.status_code == 200
        data = response.json()
        assert "avg_overall_score" in data
        assert data["num_cases"] == 1


class TestAPIValidation:
    def test_invalid_chat_history(self, client):
        response = client.post(
            "/query",
            json={
                "query": "test",
                "chat_history": [{"invalid": "format"}],
            },
        )
        assert response.status_code == 422

    def test_valid_chat_history(self, client):
        response = client.post(
            "/query",
            json={
                "query": "test",
                "chat_history": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi"},
                ],
            },
        )
        assert response.status_code == 200
