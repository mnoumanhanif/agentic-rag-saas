"""Query Analysis Agent - Classifies queries and determines retrieval needs."""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models import BaseLanguageModel

from rag_system.prompts.templates import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysis:
    """Result of query analysis."""

    needs_retrieval: bool = True
    query_type: str = "factual"
    complexity: str = "simple"
    rewritten_query: str = ""
    original_query: str = ""


class QueryAnalysisAgent:
    """Analyzes incoming queries to determine processing strategy.

    Classifies queries by type and complexity, determines whether document
    retrieval is needed, and rewrites queries for better retrieval.
    """

    def __init__(self, llm: BaseLanguageModel):
        self.llm = llm

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze a user query.

        Args:
            query: The user's input query.

        Returns:
            QueryAnalysis with classification and routing information.
        """
        analysis = QueryAnalysis(original_query=query, rewritten_query=query)

        try:
            prompt = PromptTemplates.QUERY_CLASSIFICATION.format(query=query)
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            parsed = json.loads(self._extract_json(content))
            analysis.needs_retrieval = parsed.get("needs_retrieval", True)
            analysis.query_type = parsed.get("query_type", "factual")
            analysis.complexity = parsed.get("complexity", "simple")
            analysis.rewritten_query = parsed.get("rewritten_query", query)

            logger.info(
                "Query analysis: type=%s, complexity=%s, needs_retrieval=%s",
                analysis.query_type,
                analysis.complexity,
                analysis.needs_retrieval,
            )
        except Exception as e:
            logger.warning("Query analysis failed, using defaults: %s", e)

        return analysis

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM response text.

        Args:
            text: Raw LLM response.

        Returns:
            Extracted JSON string.
        """
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return text[start:end]
        return text
