"""RAG Evaluator for comprehensive system quality assessment."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rag_system.evaluation.metrics import (
    answer_correctness,
    context_relevance,
    faithfulness_score,
    recall_at_k,
)

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of a single evaluation."""

    query: str = ""
    faithfulness: float = 0.0
    context_relevance: float = 0.0
    answer_correctness: float = 0.0
    retrieval_recall: float = 0.0
    overall_score: float = 0.0


@dataclass
class BenchmarkResult:
    """Result of a complete benchmark run."""

    results: List[EvaluationResult] = field(default_factory=list)
    avg_faithfulness: float = 0.0
    avg_context_relevance: float = 0.0
    avg_answer_correctness: float = 0.0
    avg_retrieval_recall: float = 0.0
    avg_overall_score: float = 0.0


class RAGEvaluator:
    """Evaluator for assessing RAG system quality across multiple metrics.

    Supports individual query evaluation and automated benchmarking
    over test datasets.
    """

    def evaluate_single(
        self,
        query: str,
        answer: str,
        context: str,
        reference_answer: Optional[str] = None,
        retrieved_ids: Optional[List[str]] = None,
        relevant_ids: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """Evaluate a single query-answer pair.

        Args:
            query: The original query.
            answer: Generated answer.
            context: Retrieved context used for generation.
            reference_answer: Ground truth answer (optional).
            retrieved_ids: IDs of retrieved documents (optional).
            relevant_ids: IDs of truly relevant documents (optional).

        Returns:
            EvaluationResult with individual and overall scores.
        """
        result = EvaluationResult(query=query)

        result.faithfulness = faithfulness_score(answer, context)
        result.context_relevance = context_relevance(query, context)

        if reference_answer:
            result.answer_correctness = answer_correctness(answer, reference_answer)

        if retrieved_ids and relevant_ids:
            result.retrieval_recall = recall_at_k(
                retrieved_ids, set(relevant_ids)
            )

        scores = [result.faithfulness, result.context_relevance]
        if reference_answer:
            scores.append(result.answer_correctness)
        if retrieved_ids and relevant_ids:
            scores.append(result.retrieval_recall)

        result.overall_score = sum(scores) / len(scores) if scores else 0.0

        logger.info(
            "Evaluation: faithfulness=%.2f, relevance=%.2f, overall=%.2f",
            result.faithfulness,
            result.context_relevance,
            result.overall_score,
        )
        return result

    def run_benchmark(
        self,
        test_cases: List[Dict],
    ) -> BenchmarkResult:
        """Run evaluation across a set of test cases.

        Args:
            test_cases: List of dicts with keys: query, answer, context,
                       and optionally: reference_answer, retrieved_ids, relevant_ids.

        Returns:
            BenchmarkResult with aggregate metrics.
        """
        benchmark = BenchmarkResult()

        for case in test_cases:
            result = self.evaluate_single(
                query=case.get("query", ""),
                answer=case.get("answer", ""),
                context=case.get("context", ""),
                reference_answer=case.get("reference_answer"),
                retrieved_ids=case.get("retrieved_ids"),
                relevant_ids=case.get("relevant_ids"),
            )
            benchmark.results.append(result)

        if benchmark.results:
            n = len(benchmark.results)
            benchmark.avg_faithfulness = (
                sum(r.faithfulness for r in benchmark.results) / n
            )
            benchmark.avg_context_relevance = (
                sum(r.context_relevance for r in benchmark.results) / n
            )
            benchmark.avg_answer_correctness = (
                sum(r.answer_correctness for r in benchmark.results) / n
            )
            benchmark.avg_retrieval_recall = (
                sum(r.retrieval_recall for r in benchmark.results) / n
            )
            benchmark.avg_overall_score = (
                sum(r.overall_score for r in benchmark.results) / n
            )

        logger.info(
            "Benchmark: %d cases, avg_overall=%.2f",
            len(benchmark.results),
            benchmark.avg_overall_score,
        )
        return benchmark
