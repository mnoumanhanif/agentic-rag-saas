"""Retrieval Agent - Performs advanced document retrieval."""

import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore

from rag_system.config.settings import RetrieverSettings, get_settings
from rag_system.retrievers.context_compressor import ContextCompressor
from rag_system.retrievers.hybrid_retriever import HybridRetriever
from rag_system.retrievers.multi_query_retriever import MultiQueryRetrieverWrapper
from rag_system.retrievers.reranker import Reranker

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """Orchestrates the retrieval pipeline with hybrid search, reranking, and compression.

    Combines multiple retrieval strategies for optimal document recall and precision.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        llm: BaseLanguageModel,
        documents: Optional[List[Document]] = None,
        settings: Optional[RetrieverSettings] = None,
    ):
        if settings is None:
            settings = get_settings().retriever

        self.settings = settings
        self.vector_store = vector_store
        self.llm = llm

        self.hybrid_retriever = HybridRetriever.from_vector_store(
            vector_store=vector_store,
            documents=documents,
            settings=settings,
        )

        self.multi_query = MultiQueryRetrieverWrapper(
            vector_store=vector_store,
            llm=llm,
            search_k=settings.search_k,
        )

        self.reranker = Reranker(model_name=settings.reranker_model)
        self.compressor = ContextCompressor()

    def retrieve(self, query: str) -> List[Document]:
        """Execute the full retrieval pipeline.

        Pipeline: Hybrid Search -> Multi-Query Expansion -> Reranking -> Compression

        Args:
            query: The search query.

        Returns:
            Processed and ranked list of relevant documents.
        """
        logger.info("Starting retrieval pipeline for query: %s", query[:100])

        # Step 1: Hybrid retrieval (BM25 + Dense)
        if self.settings.enable_hybrid_search:
            docs = self.hybrid_retriever.invoke(query)
        else:
            docs = self.vector_store.similarity_search(query, k=self.settings.search_k)

        logger.info("Initial retrieval: %d documents", len(docs))

        # Step 2: Multi-query expansion
        if self.settings.enable_multi_query and self.llm:
            multi_docs = self.multi_query.retrieve(query)
            seen = {d.page_content[:200] for d in docs}
            for doc in multi_docs:
                if doc.page_content[:200] not in seen:
                    docs.append(doc)
                    seen.add(doc.page_content[:200])
            logger.info("After multi-query expansion: %d documents", len(docs))

        # Step 3: Reranking
        if self.settings.enable_reranking:
            docs = self.reranker.rerank(query, docs, top_k=self.settings.search_k)
            logger.info("After reranking: %d documents", len(docs))

        # Step 4: Context compression
        if self.settings.enable_compression:
            docs = self.compressor.compress(query, docs)
            logger.info("After compression: %d documents", len(docs))

        return docs
