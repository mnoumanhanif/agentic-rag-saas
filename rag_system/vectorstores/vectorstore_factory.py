"""Factory for creating vector store instances."""

import logging
import os
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_community.vectorstores import FAISS

from rag_system.config.settings import VectorStoreSettings, get_settings

logger = logging.getLogger(__name__)


class VectorStoreFactory:
    """Factory for creating and managing vector store instances."""

    @staticmethod
    def create(
        embeddings: Embeddings,
        documents: Optional[List[Document]] = None,
        settings: Optional[VectorStoreSettings] = None,
    ) -> VectorStore:
        """Create a vector store from documents.

        Args:
            embeddings: Embedding model to use.
            documents: Documents to index. If None, attempts to load existing store.
            settings: Vector store settings. Uses global settings if not provided.

        Returns:
            A LangChain-compatible vector store instance.
        """
        if settings is None:
            settings = get_settings().vector_store

        provider = settings.provider.lower()
        logger.info("Creating vector store: provider=%s", provider)

        if provider == "faiss":
            return VectorStoreFactory._create_faiss(embeddings, documents, settings)

        if provider == "chroma":
            return VectorStoreFactory._create_chroma(embeddings, documents, settings)

        raise ValueError(f"Unsupported vector store provider: {provider}")

    @staticmethod
    def _create_faiss(
        embeddings: Embeddings,
        documents: Optional[List[Document]],
        settings: VectorStoreSettings,
    ) -> VectorStore:
        """Create or load a FAISS vector store."""
        if documents:
            store = FAISS.from_documents(documents, embeddings)
            store.save_local(settings.persist_directory)
            logger.info("Created new FAISS index with %d documents", len(documents))
            return store

        if os.path.exists(settings.persist_directory):
            logger.info("Loading existing FAISS index from %s", settings.persist_directory)
            return FAISS.load_local(
                settings.persist_directory,
                embeddings,
                allow_dangerous_deserialization=True,
            )

        raise ValueError(
            f"No documents provided and no existing FAISS index at {settings.persist_directory}"
        )

    @staticmethod
    def _create_chroma(
        embeddings: Embeddings,
        documents: Optional[List[Document]],
        settings: VectorStoreSettings,
    ) -> VectorStore:
        """Create or load a Chroma vector store."""
        from langchain_community.vectorstores import Chroma

        if documents:
            store = Chroma.from_documents(
                documents,
                embeddings,
                collection_name=settings.collection_name,
                persist_directory=settings.persist_directory,
            )
            logger.info("Created new Chroma collection with %d documents", len(documents))
            return store

        return Chroma(
            collection_name=settings.collection_name,
            embedding_function=embeddings,
            persist_directory=settings.persist_directory,
        )

    @staticmethod
    def add_documents(
        store: VectorStore,
        documents: List[Document],
        settings: Optional[VectorStoreSettings] = None,
    ) -> None:
        """Add documents to an existing vector store.

        Args:
            store: The vector store to add documents to.
            documents: Documents to add.
            settings: Vector store settings for persistence.
        """
        if settings is None:
            settings = get_settings().vector_store

        store.add_documents(documents)
        logger.info("Added %d documents to vector store", len(documents))

        if isinstance(store, FAISS):
            store.save_local(settings.persist_directory)
            logger.info("Saved FAISS index to %s", settings.persist_directory)
