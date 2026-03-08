"""Context compression for reducing irrelevant content in retrieved documents."""

import logging
from typing import List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Compresses retrieved document contexts to focus on relevant content.

    Reduces noise by extracting only the most relevant sentences from
    retrieved documents based on query relevance.
    """

    def __init__(self, max_tokens_per_doc: int = 500):
        self.max_tokens_per_doc = max_tokens_per_doc

    def compress(self, query: str, documents: List[Document]) -> List[Document]:
        """Compress documents by extracting query-relevant sentences.

        Args:
            query: The search query for relevance scoring.
            documents: Documents to compress.

        Returns:
            Documents with compressed page_content.
        """
        if not documents:
            return documents

        compressed = []
        query_terms = set(query.lower().split())

        for doc in documents:
            sentences = self._split_sentences(doc.page_content)
            scored = []
            for sentence in sentences:
                score = sum(
                    1 for term in query_terms if term in sentence.lower()
                )
                scored.append((score, sentence))

            scored.sort(key=lambda x: x[0], reverse=True)

            selected = []
            token_count = 0
            for _, sentence in scored:
                sentence_tokens = len(sentence.split())
                if token_count + sentence_tokens <= self.max_tokens_per_doc:
                    selected.append(sentence)
                    token_count += sentence_tokens

            if selected:
                compressed_content = " ".join(selected)
                compressed.append(
                    Document(
                        page_content=compressed_content,
                        metadata={**doc.metadata, "compressed": True},
                    )
                )
            else:
                truncated = " ".join(doc.page_content.split()[: self.max_tokens_per_doc])
                compressed.append(
                    Document(
                        page_content=truncated,
                        metadata={**doc.metadata, "compressed": True},
                    )
                )

        logger.info("Compressed %d documents", len(compressed))
        return compressed

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences.

        Args:
            text: Input text.

        Returns:
            List of sentences.
        """
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in ".!?" and len(current.strip()) > 10:
                sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())
        return sentences
