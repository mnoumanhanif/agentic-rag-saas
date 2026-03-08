"""Reasoning Agent - Synthesizes answers from retrieved context."""

import logging
from typing import Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel

from rag_system.prompts.templates import PromptTemplates

logger = logging.getLogger(__name__)


class ReasoningAgent:
    """Synthesizes answers from retrieved documents using chain-of-thought reasoning.

    Processes context documents and generates well-structured, cited answers.
    """

    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm

    def reason(
        self,
        query: str,
        documents: List[Document],
        chat_history: Optional[List[Dict]] = None,
    ) -> str:
        """Generate an answer by reasoning over retrieved documents.

        Args:
            query: The user's question.
            documents: Retrieved context documents.
            chat_history: Previous conversation turns.

        Returns:
            Generated answer string with source citations.
        """
        if not documents:
            return "I don't have enough context to answer this question. Please upload relevant documents first."

        context = self._format_context(documents)

        if chat_history:
            query = self._contextualize_query(query, chat_history)

        prompt = PromptTemplates.RAG_ANSWER.format(context=context, question=query)

        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            logger.info("Generated answer of length %d", len(answer))
            return answer
        except Exception as e:
            logger.error("Reasoning failed: %s", e)
            return f"I encountered an error while generating the answer: {e}"

    def _format_context(self, documents: List[Document]) -> str:
        """Format documents into a context string with source attribution.

        Args:
            documents: Documents to format.

        Returns:
            Formatted context string.
        """
        parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            parts.append(
                f"[Source {i}: {source}, Page {page}]\n{doc.page_content}\n"
            )
        return "\n".join(parts)

    def _contextualize_query(
        self, query: str, chat_history: List[Dict]
    ) -> str:
        """Rewrite a query using conversation history for context.

        Args:
            query: The follow-up question.
            chat_history: Previous conversation turns.

        Returns:
            Standalone version of the query.
        """
        history_str = ""
        for msg in chat_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_str += f"{role}: {msg.get('content', '')}\n"

        try:
            prompt = PromptTemplates.QUERY_CONTEXTUALIZATION.format(
                chat_history=history_str, question=query
            )
            response = self.llm.invoke(prompt)
            result = response.content if hasattr(response, "content") else str(response)
            logger.info("Contextualized query: %s", result[:100])
            return result
        except Exception as e:
            logger.warning("Query contextualization failed: %s", e)
            return query
