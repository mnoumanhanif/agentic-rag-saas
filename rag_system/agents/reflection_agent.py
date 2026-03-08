"""Reflection Agent - Evaluates and improves response quality."""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models import BaseLanguageModel

from rag_system.prompts.templates import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class ReflectionResult:
    """Result of answer reflection/evaluation."""

    score: float = 0.0
    is_faithful: bool = True
    has_hallucination: bool = False
    feedback: str = ""
    needs_improvement: bool = False
    improved_answer: Optional[str] = None


class ReflectionAgent:
    """Evaluates generated answers and triggers improvement if needed.

    Uses self-reflection to assess answer quality, detect hallucinations,
    and optionally regenerate improved responses.
    """

    def __init__(self, llm: BaseLanguageModel, confidence_threshold: float = 0.7):
        self.llm = llm
        self.confidence_threshold = confidence_threshold

    def reflect(self, question: str, context: str, answer: str) -> ReflectionResult:
        """Evaluate an answer for quality and accuracy.

        Args:
            question: The original question.
            context: The context used to generate the answer.
            answer: The generated answer to evaluate.

        Returns:
            ReflectionResult with quality metrics and improvement suggestions.
        """
        result = ReflectionResult()

        try:
            prompt = PromptTemplates.REFLECTION.format(
                question=question, context=context, answer=answer
            )
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            parsed = json.loads(self._extract_json(content))
            result.score = float(parsed.get("score", 0.5))
            result.is_faithful = parsed.get("is_faithful", True)
            result.has_hallucination = parsed.get("has_hallucination", False)
            result.feedback = parsed.get("feedback", "")
            result.needs_improvement = parsed.get("needs_improvement", False)

            logger.info(
                "Reflection: score=%.2f, faithful=%s, hallucination=%s",
                result.score,
                result.is_faithful,
                result.has_hallucination,
            )

            if result.needs_improvement or result.score < self.confidence_threshold:
                result.improved_answer = self._improve_answer(
                    question, context, answer, result.feedback
                )
        except Exception as e:
            logger.warning("Reflection failed: %s", e)

        return result

    def _improve_answer(
        self, question: str, context: str, original_answer: str, feedback: str
    ) -> Optional[str]:
        """Generate an improved answer based on reflection feedback.

        Args:
            question: The original question.
            context: The context documents.
            original_answer: The answer that needs improvement.
            feedback: Specific improvement suggestions.

        Returns:
            Improved answer or None if improvement fails.
        """
        try:
            improve_prompt = f"""Improve the following answer based on the feedback provided.
Stay faithful to the context and address the feedback.

Question: {question}
Context: {context}
Original Answer: {original_answer}
Feedback: {feedback}

Improved Answer:"""
            response = self.llm.invoke(improve_prompt)
            improved = response.content if hasattr(response, "content") else str(response)
            logger.info("Generated improved answer")
            return improved
        except Exception as e:
            logger.warning("Answer improvement failed: %s", e)
            return None

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
