"""Agentic RAG Pipeline - Orchestrates the full agentic retrieval and generation workflow."""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from langchain_core.language_models import BaseLanguageModel

from rag_system.agents.query_agent import QueryAnalysisAgent
from rag_system.agents.reasoning_agent import ReasoningAgent
from rag_system.agents.reflection_agent import ReflectionAgent
from rag_system.agents.retrieval_agent import RetrievalAgent
from rag_system.agents.tool_agent import ToolAgent
from rag_system.config.settings import PROVIDER_DEFAULT_MODELS, Settings, get_settings
from rag_system.pipelines.ingestion_pipeline import IngestionPipeline
from rag_system.prompts.templates import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class PipelineResponse:
    """Response from the Agentic RAG pipeline."""

    answer: str = ""
    sources: List[Dict] = field(default_factory=list)
    query_analysis: Optional[Dict] = None
    reflection: Optional[Dict] = None
    steps: List[str] = field(default_factory=list)


class AgenticRAGPipeline:
    """Main orchestrator for the Agentic RAG system.

    Coordinates query analysis, retrieval, reasoning, and reflection
    agents to produce high-quality answers from document context.
    """

    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = get_settings()

        self.settings = settings
        self.llm = self._initialize_llm()
        self.ingestion = IngestionPipeline(settings)

        # Initialize agents (lazy - some need vector store)
        self.query_agent = QueryAnalysisAgent(self.llm) if self.llm else None
        self.reasoning_agent = ReasoningAgent(self.llm) if self.llm else None
        self.reflection_agent = (
            ReflectionAgent(self.llm, settings.agent.confidence_threshold)
            if self.llm
            else None
        )
        self.tool_agent = ToolAgent()
        self._retrieval_agent: Optional[RetrievalAgent] = None

    def _initialize_llm(self) -> Optional[BaseLanguageModel]:
        """Initialize the LLM based on settings.

        Supported providers: openai, google, anthropic, groq, openrouter, ollama.

        Returns:
            Configured LLM instance or None if no API keys available.
        """
        provider = self.settings.llm.provider.lower()
        llm_cfg = self.settings.llm

        try:
            if provider == "google" and llm_cfg.google_api_key:
                from langchain_google_genai import ChatGoogleGenerativeAI

                return ChatGoogleGenerativeAI(
                    model=llm_cfg.model,
                    temperature=llm_cfg.temperature,
                )

            if provider == "openai" and llm_cfg.openai_api_key:
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=llm_cfg.model,
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                )

            if provider == "anthropic" and llm_cfg.anthropic_api_key:
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(
                    model=llm_cfg.model,
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                )

            if provider == "groq" and llm_cfg.groq_api_key:
                from langchain_groq import ChatGroq

                return ChatGroq(
                    model=llm_cfg.model,
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                )

            if provider == "openrouter" and llm_cfg.openrouter_api_key:
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=llm_cfg.model,
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                    openai_api_key=llm_cfg.openrouter_api_key,
                    openai_api_base="https://openrouter.ai/api/v1",
                )

            if provider == "ollama":
                from langchain_community.chat_models import ChatOllama

                return ChatOllama(
                    model=llm_cfg.model,
                    base_url=llm_cfg.ollama_base_url,
                    temperature=llm_cfg.temperature,
                )

            # Auto-detect available provider
            if llm_cfg.google_api_key:
                from langchain_google_genai import ChatGoogleGenerativeAI

                return ChatGoogleGenerativeAI(
                    model=PROVIDER_DEFAULT_MODELS["google"],
                    temperature=llm_cfg.temperature,
                )

            if llm_cfg.openai_api_key:
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=PROVIDER_DEFAULT_MODELS["openai"],
                    temperature=llm_cfg.temperature,
                )

            if llm_cfg.anthropic_api_key:
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(
                    model=PROVIDER_DEFAULT_MODELS["anthropic"],
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                )

            if llm_cfg.groq_api_key:
                from langchain_groq import ChatGroq

                return ChatGroq(
                    model=PROVIDER_DEFAULT_MODELS["groq"],
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                )

            if llm_cfg.openrouter_api_key:
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=PROVIDER_DEFAULT_MODELS["openrouter"],
                    temperature=llm_cfg.temperature,
                    max_tokens=llm_cfg.max_tokens,
                    openai_api_key=llm_cfg.openrouter_api_key,
                    openai_api_base="https://openrouter.ai/api/v1",
                )
        except Exception as e:
            logger.error("Failed to initialize LLM: %s", e)

        logger.warning("No LLM API keys found. Chat functionality will not work.")
        return None

    @property
    def retrieval_agent(self) -> Optional[RetrievalAgent]:
        """Lazy initialization of the retrieval agent."""
        if self._retrieval_agent is None:
            vector_store = self.ingestion.get_vector_store()
            if vector_store and self.llm:
                self._retrieval_agent = RetrievalAgent(
                    vector_store=vector_store,
                    llm=self.llm,
                    documents=self.ingestion.get_all_documents(),
                    settings=self.settings.retriever,
                )
        return self._retrieval_agent

    def ingest_pdfs(self, pdf_paths: List[str]) -> str:
        """Ingest PDF documents into the system.

        Args:
            pdf_paths: Paths to PDF files.

        Returns:
            Status message.
        """
        result = self.ingestion.ingest_pdfs(pdf_paths)
        self._retrieval_agent = None  # Reset to pick up new documents
        return result

    def query(
        self,
        query_text: str,
        chat_history: Optional[List[Dict]] = None,
    ) -> PipelineResponse:
        """Execute the full agentic RAG pipeline.

        Args:
            query_text: User's question.
            chat_history: Previous conversation turns.

        Returns:
            PipelineResponse with answer, sources, and metadata.
        """
        if chat_history is None:
            chat_history = []

        response = PipelineResponse()

        if not self.llm:
            response.answer = "LLM not initialized. Please check your API keys."
            return response

        # Step 1: Query Analysis
        if self.settings.agent.enable_query_analysis and self.query_agent:
            analysis = self.query_agent.analyze(query_text)
            response.query_analysis = {
                "needs_retrieval": analysis.needs_retrieval,
                "query_type": analysis.query_type,
                "complexity": analysis.complexity,
            }
            response.steps.append(f"Query analysis: type={analysis.query_type}")

            if not analysis.needs_retrieval:
                response.answer = self._handle_conversational(query_text, chat_history)
                response.steps.append("Handled as conversational query")
                return response

            query_text = analysis.rewritten_query or query_text

        # Step 2: Retrieval
        if not self.ingestion.get_vector_store():
            response.answer = (
                "No documents indexed. Please upload documents first."
            )
            return response

        if self.retrieval_agent:
            documents = self.retrieval_agent.retrieve(query_text)
            response.sources = [
                {
                    "content": doc.page_content[:200],
                    "metadata": doc.metadata,
                }
                for doc in documents
            ]
            response.steps.append(f"Retrieved {len(documents)} documents")
        else:
            documents = []
            response.steps.append("Retrieval agent not available")

        # Step 3: Reasoning
        if self.reasoning_agent:
            answer = self.reasoning_agent.reason(query_text, documents, chat_history)
            response.answer = answer
            response.steps.append("Generated answer via reasoning agent")
        else:
            response.answer = "Reasoning agent not available."
            return response

        # Step 4: Reflection
        if self.settings.agent.enable_reflection and self.reflection_agent:
            context = "\n".join(doc.page_content for doc in documents)
            reflection = self.reflection_agent.reflect(query_text, context, answer)
            response.reflection = {
                "score": reflection.score,
                "is_faithful": reflection.is_faithful,
                "has_hallucination": reflection.has_hallucination,
                "feedback": reflection.feedback,
            }
            response.steps.append(f"Reflection score: {reflection.score:.2f}")

            if reflection.improved_answer:
                response.answer = reflection.improved_answer
                response.steps.append("Answer improved by reflection agent")

        return response

    def _handle_conversational(
        self, query: str, chat_history: List[Dict]
    ) -> str:
        """Handle a conversational query that doesn't need retrieval.

        Args:
            query: The user's query.
            chat_history: Previous conversation turns.

        Returns:
            Conversational response.
        """
        history_str = ""
        for msg in chat_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_str += f"{role}: {msg.get('content', '')}\n"

        try:
            prompt = PromptTemplates.CONVERSATIONAL_RESPONSE.format(
                query=query, chat_history=history_str or "None"
            )
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error("Conversational response failed: %s", e)
            return f"Error generating response: {e}"
