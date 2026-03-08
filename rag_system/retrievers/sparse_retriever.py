"""Sparse retriever using BM25 keyword search."""

import logging
import math
from collections import Counter
from typing import Dict, List, Optional

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

logger = logging.getLogger(__name__)


class SparseRetriever(BaseRetriever):
    """BM25-based sparse retriever for keyword matching.

    Uses BM25 scoring to rank documents by term frequency and
    inverse document frequency relevance to the query.
    """

    documents: List[Document] = []
    search_k: int = 4
    k1: float = 1.5
    b: float = 0.75

    model_config = {"arbitrary_types_allowed": True}

    _doc_freqs: Dict[str, int] = {}
    _avg_dl: float = 0.0
    _doc_lengths: List[int] = []
    _indexed: bool = False

    def model_post_init(self, __context) -> None:
        """Build the BM25 index after initialization."""
        if self.documents:
            self._build_index()

    def _build_index(self) -> None:
        """Build BM25 index from documents."""
        if not self.documents:
            return

        self._doc_freqs = {}
        self._doc_lengths = []

        for doc in self.documents:
            terms = doc.page_content.lower().split()
            self._doc_lengths.append(len(terms))
            unique_terms = set(terms)
            for term in unique_terms:
                self._doc_freqs[term] = self._doc_freqs.get(term, 0) + 1

        total_length = sum(self._doc_lengths)
        self._avg_dl = total_length / len(self.documents) if self.documents else 1.0
        self._indexed = True
        logger.info(
            "Built BM25 index: %d docs, %d unique terms, avg_dl=%.1f",
            len(self.documents),
            len(self._doc_freqs),
            self._avg_dl,
        )

    def update_documents(self, documents: List[Document]) -> None:
        """Update the document collection and rebuild the index.

        Args:
            documents: New document list.
        """
        self.documents = documents
        self._build_index()

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Retrieve documents using BM25 scoring.

        Args:
            query: The search query.
            run_manager: Callback manager (unused).

        Returns:
            List of documents ranked by BM25 relevance score.
        """
        if not self.documents:
            return []

        if not self._indexed:
            self._build_index()

        query_terms = query.lower().split()
        n_docs = len(self.documents)
        scored_docs = []

        for idx, doc in enumerate(self.documents):
            doc_terms = Counter(doc.page_content.lower().split())
            doc_len = self._doc_lengths[idx] if idx < len(self._doc_lengths) else len(doc.page_content.split())
            score = 0.0

            for term in query_terms:
                if term not in doc_terms:
                    continue
                tf = doc_terms[term]
                df = self._doc_freqs.get(term, 0)
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                tf_norm = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * doc_len / self._avg_dl)
                )
                score += idf * tf_norm

            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        results = [doc for _, doc in scored_docs[: self.search_k]]
        logger.info("BM25 retrieval returned %d results", len(results))
        return results
