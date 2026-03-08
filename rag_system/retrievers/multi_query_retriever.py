"""Multi-query retriever for query expansion."""

import logging
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore

from rag_system.prompts.templates import PromptTemplates

logger = logging.getLogger(__name__)


class MultiQueryRetrieverWrapper:
    """Generates multiple query variants and retrieves documents for each.

    Expands a single query into multiple perspectives to improve recall.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        llm: BaseLanguageModel,
        num_queries: int = 3,
        search_k: int = 4,
    ):
        self.vector_store = vector_store
        self.llm = llm
        self.num_queries = num_queries
        self.search_k = search_k

    def retrieve(self, query: str) -> List[Document]:
        """Generate multiple queries and retrieve documents for each.

        Args:
            query: The original user query.

        Returns:
            Deduplicated list of relevant documents from all query variants.
        """
        queries = self._generate_queries(query)
        logger.info("Generated %d query variants", len(queries))

        all_docs: List[Document] = []
        seen_content: set = set()

        for q in queries:
            docs = self.vector_store.similarity_search(q, k=self.search_k)
            for doc in docs:
                content_key = doc.page_content[:200]
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    all_docs.append(doc)

        logger.info("Multi-query retrieval returned %d unique documents", len(all_docs))
        return all_docs[: self.search_k * 2]

    def _generate_queries(self, query: str) -> List[str]:
        """Generate alternative query formulations using the LLM.

        Args:
            query: The original query.

        Returns:
            List of alternative queries including the original.
        """
        queries = [query]

        try:
            prompt = PromptTemplates.MULTI_QUERY_GENERATION.format(
                question=query, num_queries=self.num_queries
            )
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            for line in content.strip().split("\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    cleaned = line.lstrip("0123456789.)- ").strip()
                    if cleaned:
                        queries.append(cleaned)
        except Exception as e:
            logger.warning("Failed to generate multi-queries: %s", e)

        return queries
