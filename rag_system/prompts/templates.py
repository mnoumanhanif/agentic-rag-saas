"""Modular prompt templates for the Agentic RAG system."""

from langchain_core.prompts import PromptTemplate


class PromptTemplates:
    """Collection of prompt templates used throughout the system."""

    QUERY_CLASSIFICATION = PromptTemplate(
        template="""Analyze the following user query and classify it.

Query: {query}

Respond with a JSON object containing:
- "needs_retrieval": boolean - whether this query needs document retrieval
- "query_type": string - one of "factual", "analytical", "conversational", "creative"
- "complexity": string - one of "simple", "moderate", "complex"
- "rewritten_query": string - an optimized version of the query for retrieval

Respond ONLY with valid JSON, no other text.""",
        input_variables=["query"],
    )

    QUERY_CONTEXTUALIZATION = PromptTemplate(
        template="""Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.

Chat History:
{chat_history}

Follow Up Input: {question}

Standalone question:""",
        input_variables=["chat_history", "question"],
    )

    MULTI_QUERY_GENERATION = PromptTemplate(
        template="""You are an AI assistant helping to generate multiple search queries.
Given the original question, generate {num_queries} different versions of the question
that could help retrieve relevant documents. Each version should approach the topic
from a different angle.

Original question: {question}

Provide {num_queries} alternative questions, one per line, numbered 1 to {num_queries}.
Do not include any other text.""",
        input_variables=["question", "num_queries"],
    )

    RAG_ANSWER = PromptTemplate(
        template="""Use the following pieces of context to answer the question at the end.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Provide citations by referencing the source documents when possible.

Context:
{context}

Question: {question}

Instructions:
- Answer based ONLY on the provided context
- If the context doesn't contain enough information, say so
- Include source references where applicable
- Be concise but thorough

Answer:""",
        input_variables=["context", "question"],
    )

    REFLECTION = PromptTemplate(
        template="""Evaluate the following answer for quality and accuracy.

Question: {question}
Context used: {context}
Generated answer: {answer}

Evaluate on these criteria:
1. Faithfulness: Does the answer stick to the provided context?
2. Completeness: Does it fully address the question?
3. Clarity: Is it clear and well-structured?
4. Hallucination: Does it contain information not in the context?

Respond with a JSON object containing:
- "score": float between 0 and 1
- "is_faithful": boolean
- "has_hallucination": boolean
- "feedback": string with specific improvement suggestions
- "needs_improvement": boolean

Respond ONLY with valid JSON, no other text.""",
        input_variables=["question", "context", "answer"],
    )

    QUERY_REWRITE = PromptTemplate(
        template="""Rewrite the following query to be more specific and effective for document retrieval.
Remove ambiguity and add relevant context.

Original query: {query}

Rewritten query:""",
        input_variables=["query"],
    )

    CONVERSATIONAL_RESPONSE = PromptTemplate(
        template="""You are a helpful AI assistant. Respond to the following conversational query.
This query does not require document retrieval.

Query: {query}

Chat History:
{chat_history}

Provide a helpful, friendly response:""",
        input_variables=["query", "chat_history"],
    )
