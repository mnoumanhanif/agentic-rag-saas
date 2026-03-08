"""Factory for creating embedding models."""

import logging
from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from rag_system.config.settings import EmbeddingSettings, get_settings

logger = logging.getLogger(__name__)


class EmbeddingFactory:
    """Factory for creating embedding model instances."""

    @staticmethod
    def create(settings: Optional[EmbeddingSettings] = None) -> Embeddings:
        """Create an embedding model based on settings.

        Args:
            settings: Embedding settings. Uses global settings if not provided.

        Returns:
            A LangChain-compatible embedding model instance.
        """
        if settings is None:
            settings = get_settings().embedding

        provider = settings.provider.lower()
        logger.info("Creating embedding model: provider=%s, model=%s", provider, settings.model_name)

        if provider == "huggingface":
            return HuggingFaceEmbeddings(model_name=settings.model_name)

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(model=settings.model_name)

        raise ValueError(f"Unsupported embedding provider: {provider}")
