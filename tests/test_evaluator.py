"""Tests for the evaluation module - RAGEvaluator."""

from rag_system.evaluation.evaluator import RAGEvaluator


class TestRAGEvaluator:
    def test_evaluate_single(self):
        evaluator = RAGEvaluator()
        result = evaluator.evaluate_single(
            query="What is Python?",
            answer="Python is a programming language used for development",
            context="Python is a popular programming language used for software development",
        )
        assert result.faithfulness > 0
        assert result.context_relevance > 0
        assert result.overall_score > 0

    def test_evaluate_with_reference(self):
        evaluator = RAGEvaluator()
        result = evaluator.evaluate_single(
            query="What is Python?",
            answer="Python is a programming language",
            context="Python is a popular programming language",
            reference_answer="Python is a programming language",
        )
        assert result.answer_correctness > 0

    def test_benchmark(self):
        evaluator = RAGEvaluator()
        test_cases = [
            {
                "query": "What is AI?",
                "answer": "AI is artificial intelligence",
                "context": "Artificial intelligence (AI) is a field of computer science",
            },
            {
                "query": "What is ML?",
                "answer": "ML is machine learning",
                "context": "Machine learning (ML) is a subset of AI",
            },
        ]
        result = evaluator.run_benchmark(test_cases)
        assert len(result.results) == 2
        assert result.avg_overall_score > 0

    def test_empty_benchmark(self):
        evaluator = RAGEvaluator()
        result = evaluator.run_benchmark([])
        assert len(result.results) == 0
        assert result.avg_overall_score == 0.0
