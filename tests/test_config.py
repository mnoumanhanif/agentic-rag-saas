"""Tests for the configuration module."""

import os
from unittest.mock import patch

from rag_system.config.settings import (
    AgentSettings,
    APISettings,
    ChunkingSettings,
    EmbeddingSettings,
    LLMSettings,
    RetrieverSettings,
    Settings,
    VectorStoreSettings,
    get_settings,
    reset_settings,
)


class TestLLMSettings:
    def test_default_provider(self):
        s = LLMSettings()
        assert s.provider == "openai"
        assert s.model == "gpt-3.5-turbo"
        assert s.temperature == 0.3

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False)
    def test_auto_detect_google(self):
        s = LLMSettings(openai_api_key=None, google_api_key=None)
        assert s.provider == "google"
        assert s.model == "gemini-2.5-flash"
        assert s.google_api_key == "test-key"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False)
    def test_auto_detect_anthropic(self):
        s = LLMSettings(openai_api_key=None, anthropic_api_key=None)
        assert s.provider == "anthropic"
        assert s.model == "claude-sonnet-4-20250514"
        assert s.anthropic_api_key == "test-key"

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=False)
    def test_auto_detect_groq(self):
        s = LLMSettings(openai_api_key=None, groq_api_key=None)
        assert s.provider == "groq"
        assert s.model == "llama-3.3-70b-versatile"
        assert s.groq_api_key == "test-key"

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False)
    def test_auto_detect_openrouter(self):
        s = LLMSettings(openai_api_key=None, openrouter_api_key=None)
        assert s.provider == "openrouter"
        assert s.model == "google/gemini-2.5-flash"
        assert s.openrouter_api_key == "test-key"

    def test_explicit_provider_preserved(self):
        s = LLMSettings(provider="ollama", model="llama3")
        assert s.provider == "ollama"
        assert s.model == "llama3"

    def test_openai_key_prevents_auto_detect(self):
        """When OpenAI key is set, don't auto-switch to other providers."""
        s = LLMSettings(
            openai_api_key="oai-key", anthropic_api_key="ant-key", google_api_key=None
        )
        assert s.provider == "openai"
        assert s.model == "gpt-3.5-turbo"

    def test_ollama_base_url_default(self):
        s = LLMSettings()
        assert s.ollama_base_url == "http://localhost:11434"


class TestEmbeddingSettings:
    def test_defaults(self):
        s = EmbeddingSettings()
        assert s.provider == "huggingface"
        assert s.model_name == "all-MiniLM-L6-v2"
        assert s.dimension == 384


class TestVectorStoreSettings:
    def test_defaults(self):
        s = VectorStoreSettings()
        assert s.provider == "faiss"
        assert s.persist_directory == "faiss_index"


class TestRetrieverSettings:
    def test_defaults(self):
        s = RetrieverSettings()
        assert s.search_k == 4
        assert s.enable_hybrid_search is True
        assert s.enable_reranking is True
        assert s.bm25_weight == 0.3
        assert s.dense_weight == 0.7


class TestChunkingSettings:
    def test_defaults(self):
        s = ChunkingSettings()
        assert s.chunk_size == 600
        assert s.chunk_overlap == 80
        assert len(s.separators) > 0


class TestAgentSettings:
    def test_defaults(self):
        s = AgentSettings()
        assert s.enable_query_analysis is True
        assert s.enable_reflection is True
        assert s.max_reasoning_steps == 5
        assert s.confidence_threshold == 0.7


class TestAPISettings:
    def test_defaults(self):
        s = APISettings()
        assert s.host == "0.0.0.0"
        assert s.port == 8000
        assert s.rate_limit_requests == 60


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert isinstance(s.llm, LLMSettings)
        assert isinstance(s.embedding, EmbeddingSettings)
        assert isinstance(s.vector_store, VectorStoreSettings)
        assert s.log_level == "INFO"
        assert s.debug is False


class TestGetSettings:
    def test_singleton(self):
        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset(self):
        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2
