"""Hybrid retriever combining BM25 (sparse) and dense vector search."""

import logging
from typing import List, Optional

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore

from rag_system.config.settings import RetrieverSettings, get_settings
from rag_system.retrievers.dense_retriever import DenseRetriever
from rag_system.retrievers.sparse_retriever import SparseRetriever

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """Retriever that combines BM25 sparse search with dense vector search.

    Uses reciprocal rank fusion to merge results from both retrieval methods.

    Hybrid Score = α * Dense Similarity + β * BM25 Score
    where α = dense_weight and β = bm25_weight.
    """

    vector_store: VectorStore
    documents: List[Document] = []
    bm25_weight: float = 0.3
    dense_weight: float = 0.7
    search_k: int = 4

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_vector_store(
        cls,
        vector_store: VectorStore,
        documents: Optional[List[Document]] = None,
        settings: Optional[RetrieverSettings] = None,
    ) -> "HybridRetriever":
        """Create a hybrid retriever from a vector store.

        Args:
            vector_store: The dense vector store to use.
            documents: Documents for BM25 indexing. If None, dense-only mode.
            settings: Retriever settings.

        Returns:
            A configured HybridRetriever instance.
        """
        if settings is None:
            settings = get_settings().retriever

        return cls(
            vector_store=vector_store,
            documents=documents or [],
            bm25_weight=settings.bm25_weight,
            dense_weight=settings.dense_weight,
            search_k=settings.search_k,
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Retrieve documents using hybrid search.

        Args:
            query: The search query.
            run_manager: Callback manager (unused).

        Returns:
            List of relevant documents, ranked by combined score.
        """
        # Use dedicated dense retriever
        dense_retriever = DenseRetriever.from_vector_store(
            self.vector_store, search_k=self.search_k
        )
        dense_results = dense_retriever.invoke(query)
        logger.info("Dense retrieval returned %d results", len(dense_results))

        if not self.documents:
            return dense_results

        # Use dedicated sparse retriever
        sparse_retriever = SparseRetriever(
            documents=self.documents, search_k=self.search_k
        )
        bm25_results = sparse_retriever.invoke(query)
        logger.info("BM25 retrieval returned %d results", len(bm25_results))

        return self._reciprocal_rank_fusion(dense_results, bm25_results)

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Document],
        sparse_results: List[Document],
        k: int = 60,
    ) -> List[Document]:
        """Merge results using Reciprocal Rank Fusion (RRF).

        Hybrid Score = α / (k + rank_dense) + β / (k + rank_sparse)

        Args:
            dense_results: Results from dense vector search.
            sparse_results: Results from BM25 search.
            k: RRF constant (default 60).

        Returns:
            Merged and re-ranked list of documents.
        """
        doc_scores: dict = {}
        doc_map: dict = {}

        for rank, doc in enumerate(dense_results):
            doc_id = doc.page_content[:100]
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + self.dense_weight / (k + rank + 1)
            doc_map[doc_id] = doc

        for rank, doc in enumerate(sparse_results):
            doc_id = doc.page_content[:100]
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + self.bm25_weight / (k + rank + 1)
            doc_map[doc_id] = doc

        sorted_ids = sorted(doc_scores, key=lambda x: doc_scores[x], reverse=True)
        return [doc_map[doc_id] for doc_id in sorted_ids[: self.search_k]]
