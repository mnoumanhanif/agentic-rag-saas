"""Tests for evaluation metrics."""

import pytest

from rag_system.evaluation.metrics import (
    answer_correctness,
    context_relevance,
    faithfulness_score,
    recall_at_k,
)


class TestRecallAtK:
    def test_perfect_recall(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=3) == 1.0

    def test_no_recall(self):
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_partial_recall(self):
        retrieved = ["a", "x", "b"]
        relevant = {"a", "b", "c"}
        assert recall_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)

    def test_empty_relevant(self):
        assert recall_at_k(["a", "b"], set(), k=2) == 0.0

    def test_k_limits(self):
        retrieved = ["a", "b", "c", "d"]
        relevant = {"c", "d"}
        assert recall_at_k(retrieved, relevant, k=2) == 0.0
        assert recall_at_k(retrieved, relevant, k=4) == 1.0


class TestFaithfulnessScore:
    def test_perfect_overlap(self):
        context = "Python is a programming language"
        answer = "Python is a programming language"
        score = faithfulness_score(answer, context)
        assert score > 0.5

    def test_no_overlap(self):
        context = "apples oranges bananas grapes"
        answer = "cars trains planes boats"
        score = faithfulness_score(answer, context)
        assert score == 0.0

    def test_empty_inputs(self):
        assert faithfulness_score("", "context") == 0.0
        assert faithfulness_score("answer", "") == 0.0


class TestContextRelevance:
    def test_relevant(self):
        query = "machine learning algorithms"
        context = "Machine learning algorithms are used for prediction"
        score = context_relevance(query, context)
        assert score > 0.5

    def test_irrelevant(self):
        query = "quantum physics"
        context = "Cooking recipes for pasta"
        score = context_relevance(query, context)
        assert score == 0.0

    def test_empty(self):
        assert context_relevance("", "context") == 0.0
        assert context_relevance("query", "") == 0.0


class TestAnswerCorrectness:
    def test_identical(self):
        text = "The capital of France is Paris"
        score = answer_correctness(text, text)
        assert score == 1.0

    def test_partial(self):
        answer = "Paris is the capital"
        reference = "The capital of France is Paris"
        score = answer_correctness(answer, reference)
        assert 0 < score < 1

    def test_empty(self):
        assert answer_correctness("", "reference") == 0.0
        assert answer_correctness("answer", "") == 0.0
