"""Individual evaluation metrics for RAG system quality assessment."""

import logging
from typing import List, Set

logger = logging.getLogger(__name__)


def recall_at_k(
    retrieved_ids: List[str],
    relevant_ids: Set[str],
    k: int = 4,
) -> float:
    """Calculate Recall@k for retrieval evaluation.

    Args:
        retrieved_ids: IDs of retrieved documents (in order).
        relevant_ids: Set of IDs of truly relevant documents.
        k: Number of top results to consider.

    Returns:
        Recall@k score between 0 and 1.
    """
    if not relevant_ids:
        return 0.0

    top_k = set(retrieved_ids[:k])
    relevant_retrieved = top_k & relevant_ids
    return len(relevant_retrieved) / len(relevant_ids)


def faithfulness_score(answer: str, context: str) -> float:
    """Estimate faithfulness of an answer to its context.

    Simple heuristic: measures overlap between answer tokens and context tokens.

    Args:
        answer: Generated answer.
        context: Source context.

    Returns:
        Faithfulness score between 0 and 1.
    """
    if not answer or not context:
        return 0.0

    answer_tokens = set(answer.lower().split())
    context_tokens = set(context.lower().split())

    # Remove common stop words for better signal
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "and",
        "but", "or", "nor", "not", "so", "yet", "both", "either",
        "neither", "each", "every", "all", "any", "few", "more",
        "most", "other", "some", "such", "no", "only", "own", "same",
        "than", "too", "very", "just", "because", "if", "when", "it",
        "this", "that", "these", "those", "i", "you", "he", "she",
        "we", "they", "me", "him", "her", "us", "them",
    }

    answer_tokens -= stop_words
    context_tokens -= stop_words

    if not answer_tokens:
        return 0.0

    overlap = answer_tokens & context_tokens
    return len(overlap) / len(answer_tokens)


def context_relevance(query: str, context: str) -> float:
    """Estimate relevance of retrieved context to the query.

    Args:
        query: The search query.
        context: Retrieved context.

    Returns:
        Relevance score between 0 and 1.
    """
    if not query or not context:
        return 0.0

    query_tokens = set(query.lower().split())
    context_tokens = set(context.lower().split())

    if not query_tokens:
        return 0.0

    overlap = query_tokens & context_tokens
    return len(overlap) / len(query_tokens)


def answer_correctness(answer: str, reference: str) -> float:
    """Estimate answer correctness compared to a reference answer.

    Uses token overlap as a simple correctness metric (F1-like).

    Args:
        answer: Generated answer.
        reference: Reference/ground truth answer.

    Returns:
        Correctness score between 0 and 1.
    """
    if not answer or not reference:
        return 0.0

    answer_tokens = set(answer.lower().split())
    reference_tokens = set(reference.lower().split())

    if not answer_tokens or not reference_tokens:
        return 0.0

    overlap = answer_tokens & reference_tokens
    precision = len(overlap) / len(answer_tokens) if answer_tokens else 0
    recall = len(overlap) / len(reference_tokens) if reference_tokens else 0

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)
