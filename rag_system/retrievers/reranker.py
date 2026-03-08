"""Cross-encoder reranker for improving retrieval precision."""

import logging
from typing import List, Optional, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


_LOAD_FAILED = object()  # Sentinel to avoid retrying failed loads


class Reranker:
    """Reranks retrieved documents using a cross-encoder model.

    Cross-encoders jointly encode query-document pairs for more accurate
    relevance scoring compared to bi-encoder similarity.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy-load the cross-encoder model."""
        if self._model is _LOAD_FAILED:
            return None
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
                logger.info("Loaded reranker model: %s", self.model_name)
            except Exception as e:
                logger.warning("Could not load reranker model: %s", e)
                self._model = _LOAD_FAILED
                return None
        return self._model

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: Optional[int] = None,
    ) -> List[Document]:
        """Rerank documents by relevance to the query.

        Args:
            query: The search query.
            documents: Documents to rerank.
            top_k: Number of top documents to return. Returns all if None.

        Returns:
            Documents sorted by relevance score (highest first).
        """
        if not documents:
            return documents

        if self.model is None:
            logger.warning("Reranker model not available, returning original order")
            return documents

        pairs = [[query, doc.page_content] for doc in documents]
        scores = self.model.predict(pairs)

        scored_docs: List[Tuple[float, Document]] = list(zip(scores, documents))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        if top_k is not None:
            scored_docs = scored_docs[:top_k]

        logger.info(
            "Reranked %d documents, top score: %.4f",
            len(scored_docs),
            scored_docs[0][0] if scored_docs else 0,
        )
        return [doc for _, doc in scored_docs]
