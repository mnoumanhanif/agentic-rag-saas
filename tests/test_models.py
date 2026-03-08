"""Tests for the API models."""

import pytest
from pydantic import ValidationError

from rag_system.api.models import QueryRequest, QueryResponse


class TestQueryRequest:
    def test_valid_request(self):
        req = QueryRequest(query="What is AI?")
        assert req.query == "What is AI?"
        assert req.chat_history == []

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="")

    def test_whitespace_only_rejected(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="   ")

    def test_valid_chat_history(self):
        req = QueryRequest(
            query="test",
            chat_history=[{"role": "user", "content": "hello"}],
        )
        assert len(req.chat_history) == 1

    def test_invalid_role(self):
        with pytest.raises(ValidationError):
            QueryRequest(
                query="test",
                chat_history=[{"role": "system", "content": "hello"}],
            )

    def test_missing_content(self):
        with pytest.raises(ValidationError):
            QueryRequest(
                query="test",
                chat_history=[{"role": "user"}],
            )


class TestQueryResponse:
    def test_valid_response(self):
        resp = QueryResponse(answer="Test answer")
        assert resp.answer == "Test answer"
        assert resp.sources == []
        assert resp.steps == []
