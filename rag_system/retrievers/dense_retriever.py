"""Dense retriever using vector similarity search."""

import logging
from typing import List, Optional

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore

logger = logging.getLogger(__name__)


class DenseRetriever(BaseRetriever):
    """Retriever that performs dense vector similarity search.

    Embeds the query and finds the most similar documents using
    cosine similarity in the vector space.
    """

    vector_store: VectorStore
    search_k: int = 4

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def from_vector_store(
        cls,
        vector_store: VectorStore,
        search_k: int = 4,
    ) -> "DenseRetriever":
        """Create a dense retriever from a vector store.

        Args:
            vector_store: The vector store to search.
            search_k: Number of top results to return.

        Returns:
            A configured DenseRetriever instance.
        """
        return cls(vector_store=vector_store, search_k=search_k)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Retrieve documents using dense vector similarity.

        Args:
            query: The search query.
            run_manager: Callback manager (unused).

        Returns:
            List of relevant documents ranked by vector similarity.
        """
        results = self.vector_store.similarity_search(query, k=self.search_k)
        logger.info("Dense retrieval returned %d results", len(results))
        return results
