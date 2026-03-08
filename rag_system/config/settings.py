"""Centralized settings management for the Agentic RAG system."""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Default models per provider (single source of truth)
PROVIDER_DEFAULT_MODELS = {
    "openai": "gpt-3.5-turbo",
    "google": "gemini-2.5-flash",
    "anthropic": "claude-sonnet-4-20250514",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "google/gemini-2.5-flash",
    "ollama": "llama3",
}


@dataclass
class LLMSettings:
    """LLM configuration.

    Supported providers: openai, google, anthropic, groq, openrouter, ollama.
    The system auto-detects the provider from whichever API key is set.
    """

    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.3
    max_tokens: int = 2048
    openai_api_key: Optional[str] = field(default=None, repr=False)
    google_api_key: Optional[str] = field(default=None, repr=False)
    anthropic_api_key: Optional[str] = field(default=None, repr=False)
    groq_api_key: Optional[str] = field(default=None, repr=False)
    openrouter_api_key: Optional[str] = field(default=None, repr=False)
    ollama_base_url: str = "http://localhost:11434"

    def __post_init__(self):
        self.openai_api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.google_api_key = self.google_api_key or os.getenv("GOOGLE_API_KEY")
        self.anthropic_api_key = self.anthropic_api_key or os.getenv(
            "ANTHROPIC_API_KEY"
        )
        self.groq_api_key = self.groq_api_key or os.getenv("GROQ_API_KEY")
        self.openrouter_api_key = self.openrouter_api_key or os.getenv(
            "OPENROUTER_API_KEY"
        )

        # Auto-detect provider when the default (openai) has no key set.
        # If the user explicitly provided an OpenAI key, keep the default.
        if not self.openai_api_key:
            if self.google_api_key:
                self.provider = "google"
                self.model = PROVIDER_DEFAULT_MODELS["google"]
            elif self.anthropic_api_key:
                self.provider = "anthropic"
                self.model = PROVIDER_DEFAULT_MODELS["anthropic"]
            elif self.groq_api_key:
                self.provider = "groq"
                self.model = PROVIDER_DEFAULT_MODELS["groq"]
            elif self.openrouter_api_key:
                self.provider = "openrouter"
                self.model = PROVIDER_DEFAULT_MODELS["openrouter"]


@dataclass
class EmbeddingSettings:
    """Embedding model configuration."""

    provider: str = "huggingface"  # huggingface, openai
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384


@dataclass
class VectorStoreSettings:
    """Vector store configuration."""

    provider: str = "faiss"  # faiss, chroma
    persist_directory: str = "faiss_index"
    collection_name: str = "rag_documents"


@dataclass
class RetrieverSettings:
    """Retriever configuration."""

    search_k: int = 4
    enable_hybrid_search: bool = True
    enable_reranking: bool = True
    enable_multi_query: bool = True
    enable_compression: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    bm25_weight: float = 0.3
    dense_weight: float = 0.7


@dataclass
class ChunkingSettings:
    """Document chunking configuration."""

    chunk_size: int = 600
    chunk_overlap: int = 80
    separators: list = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])


@dataclass
class AgentSettings:
    """Agent behavior configuration."""

    enable_query_analysis: bool = True
    enable_reflection: bool = True
    enable_tool_use: bool = True
    max_reasoning_steps: int = 5
    confidence_threshold: float = 0.7


@dataclass
class SecuritySettings:
    """Security configuration."""

    require_api_key: bool = False
    enable_prompt_injection_detection: bool = True
    enable_security_headers: bool = True
    enable_ip_throttle: bool = True
    ip_throttle_max_requests: int = 120
    ip_throttle_window_seconds: int = 60
    allowed_upload_extensions: list = field(default_factory=lambda: [".pdf"])
    max_query_length: int = 5000


@dataclass
class BatchEmbeddingSettings:
    """Batch embedding configuration for improved throughput."""

    batch_size: int = 32
    show_progress: bool = False


@dataclass
class WorkerSettings:
    """Background worker configuration for async task processing."""

    enabled: bool = False
    queue_name: str = "default"
    job_timeout: int = 600


@dataclass
class RedisSettings:
    """Redis configuration for caching and task queues."""

    url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    enabled: bool = False


@dataclass
class APISettings:
    """API server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    max_upload_size_mb: int = 50
    cors_origins: list = field(default_factory=lambda: ["*"])
    workers: int = 1


@dataclass
class Settings:
    """Root configuration for the Agentic RAG system."""

    llm: LLMSettings = field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = field(default_factory=EmbeddingSettings)
    batch_embedding: BatchEmbeddingSettings = field(default_factory=BatchEmbeddingSettings)
    vector_store: VectorStoreSettings = field(default_factory=VectorStoreSettings)
    retriever: RetrieverSettings = field(default_factory=RetrieverSettings)
    chunking: ChunkingSettings = field(default_factory=ChunkingSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    api: APISettings = field(default_factory=APISettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    worker: WorkerSettings = field(default_factory=WorkerSettings)
    log_level: str = "INFO"
    debug: bool = False


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings():
    """Reset global settings (useful for testing)."""
    global _settings
    _settings = None
