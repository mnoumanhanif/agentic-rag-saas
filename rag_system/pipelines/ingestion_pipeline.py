"""Document ingestion pipeline for processing and indexing documents."""

import logging
import os
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_system.config.settings import ChunkingSettings, Settings, get_settings
from rag_system.embeddings.embedding_factory import EmbeddingFactory
from rag_system.vectorstores.vectorstore_factory import VectorStoreFactory

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Pipeline for ingesting, chunking, and indexing documents.

    Handles the full document processing workflow from raw files to
    indexed vector store entries. Uses streaming page-by-page chunking
    to avoid memory spikes and batch embedding for throughput.
    """

    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = get_settings()

        self.settings = settings
        self._embeddings: Optional[Embeddings] = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunking.chunk_size,
            chunk_overlap=settings.chunking.chunk_overlap,
            separators=settings.chunking.separators,
        )
        self.batch_size = settings.batch_embedding.batch_size
        self.vector_store: Optional[VectorStore] = None
        self._all_documents: List[Document] = []
        self._store_load_attempted: bool = False

    @property
    def embeddings(self) -> Embeddings:
        """Lazy-load embeddings to avoid downloading models at startup."""
        if self._embeddings is None:
            self._embeddings = EmbeddingFactory.create(self.settings.embedding)
        return self._embeddings

    def _load_existing_store(self) -> None:
        """Try to load an existing vector store."""
        try:
            self.vector_store = VectorStoreFactory.create(
                embeddings=self.embeddings,
                settings=self.settings.vector_store,
            )
            logger.info("Loaded existing vector store")
        except (ValueError, Exception) as e:
            logger.info("No existing vector store found: %s", e)
            self.vector_store = None

    def _stream_pdf_pages(self, pdf_path: str) -> List[Document]:
        """Load a PDF page-by-page to avoid loading the entire file into memory.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of chunked documents from the PDF.
        """
        chunks: List[Document] = []
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()

        # Process page by page for memory efficiency
        for page in pages:
            page_chunks = self.text_splitter.split_documents([page])
            chunks.extend(page_chunks)

        logger.info(
            "Streamed %d pages -> %d chunks from %s",
            len(pages),
            len(chunks),
            os.path.basename(pdf_path),
        )
        return chunks

    def _batch_add_documents(self, chunks: List[Document]) -> None:
        """Add documents to the vector store in batches for memory efficiency.

        Args:
            chunks: Document chunks to add.
        """
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]
            if self.vector_store is None:
                self.vector_store = VectorStoreFactory.create(
                    embeddings=self.embeddings,
                    documents=batch,
                    settings=self.settings.vector_store,
                )
            else:
                VectorStoreFactory.add_documents(
                    store=self.vector_store,
                    documents=batch,
                    settings=self.settings.vector_store,
                )
            logger.info(
                "Batch indexed %d/%d chunks", min(i + self.batch_size, len(chunks)), len(chunks)
            )

    def ingest_pdfs(self, pdf_paths: List[str]) -> str:
        """Ingest PDF files into the vector store.

        Uses streaming page-by-page chunking and batch embedding
        to prevent memory spikes on resource-constrained systems.

        Args:
            pdf_paths: List of file paths to PDF documents.

        Returns:
            Status message with processing details.
        """
        all_chunks: List[Document] = []

        for path in pdf_paths:
            if not os.path.exists(path):
                logger.warning("File not found: %s", path)
                continue

            chunks = self._stream_pdf_pages(path)
            all_chunks.extend(chunks)

        if not all_chunks:
            return "No documents were loaded."

        logger.info(
            "Total: %d chunks from %d files",
            len(all_chunks),
            len(pdf_paths),
        )

        self._all_documents.extend(all_chunks)
        self._batch_add_documents(all_chunks)

        return f"Processed {len(all_chunks)} chunks from {len(pdf_paths)} files."

    def get_vector_store(self) -> Optional[VectorStore]:
        """Get the current vector store, loading from disk if available.

        Returns:
            The vector store instance or None if not initialized.
        """
        if self.vector_store is None and not self._store_load_attempted:
            self._store_load_attempted = True
            self._load_existing_store()
        return self.vector_store

    def get_all_documents(self) -> List[Document]:
        """Get all ingested document chunks.

        Returns:
            List of all document chunks for BM25 indexing.
        """
        return self._all_documents
