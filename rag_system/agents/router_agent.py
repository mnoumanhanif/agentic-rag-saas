"""Router Agent - Routes queries to appropriate retrieval strategies and tools."""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from langchain_core.language_models import BaseLanguageModel

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Result of the routing decision."""

    use_dense_retrieval: bool = True
    use_sparse_retrieval: bool = True
    use_tools: List[str] = field(default_factory=list)
    reasoning: str = ""


class RouterAgent:
    """Routes queries to the appropriate retrieval strategy and tools.

    Determines whether to use dense retrieval, sparse retrieval,
    tool calls, or a combination based on query analysis.
    """

    ROUTING_PROMPT = """Analyze the following query and determine the best retrieval strategy.

Query: {query}

Determine:
1. Should we use dense (semantic) retrieval? Good for conceptual/meaning-based questions.
2. Should we use sparse (keyword/BM25) retrieval? Good for specific terms, names, numbers.
3. Should we use any tools? Available tools: {tools}

Respond with a JSON object:
{{
    "use_dense_retrieval": boolean,
    "use_sparse_retrieval": boolean,
    "use_tools": [list of tool names to use, or empty list],
    "reasoning": "brief explanation of routing decision"
}}

Respond ONLY with valid JSON, no other text."""

    def __init__(self, llm: Optional[BaseLanguageModel] = None, available_tools: Optional[List[str]] = None):
        self.llm = llm
        self.available_tools = available_tools or ["calculator", "datetime"]

    def route(self, query: str) -> RoutingDecision:
        """Determine the retrieval strategy for a query.

        Args:
            query: The user's query.

        Returns:
            RoutingDecision with strategy selections.
        """
        # Default: use both retrieval methods
        decision = RoutingDecision()

        if not self.llm:
            return self._rule_based_routing(query)

        try:
            prompt = self.ROUTING_PROMPT.format(
                query=query,
                tools=", ".join(self.available_tools),
            )
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            parsed = json.loads(self._extract_json(content))
            decision.use_dense_retrieval = parsed.get("use_dense_retrieval", True)
            decision.use_sparse_retrieval = parsed.get("use_sparse_retrieval", True)
            decision.use_tools = parsed.get("use_tools", [])
            decision.reasoning = parsed.get("reasoning", "")

            logger.info(
                "Routing decision: dense=%s, sparse=%s, tools=%s",
                decision.use_dense_retrieval,
                decision.use_sparse_retrieval,
                decision.use_tools,
            )
        except Exception as e:
            logger.warning("Router agent failed, using defaults: %s", e)
            decision = self._rule_based_routing(query)

        return decision

    def _rule_based_routing(self, query: str) -> RoutingDecision:
        """Apply simple rule-based routing when LLM is unavailable.

        Args:
            query: The user's query.

        Returns:
            RoutingDecision based on heuristics.
        """
        decision = RoutingDecision()
        query_lower = query.lower()

        # Check for calculation-related queries
        math_keywords = ["calculate", "compute", "sum", "average", "total", "how much", "how many"]
        if any(kw in query_lower for kw in math_keywords):
            decision.use_tools.append("calculator")

        # Check for date/time queries
        time_keywords = ["what time", "what date", "today", "current date", "current time"]
        if any(kw in query_lower for kw in time_keywords):
            decision.use_tools.append("datetime")

        # Specific term/number queries favor sparse retrieval
        has_specific_terms = any(c.isupper() for c in query[1:]) or any(c.isdigit() for c in query)
        if has_specific_terms:
            decision.use_sparse_retrieval = True

        decision.reasoning = "Rule-based routing (LLM unavailable)"
        return decision

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
