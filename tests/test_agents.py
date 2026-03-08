"""Tests for the agents module."""

from unittest.mock import MagicMock, patch

from rag_system.agents.query_agent import QueryAnalysis, QueryAnalysisAgent
from rag_system.agents.reasoning_agent import ReasoningAgent
from rag_system.agents.reflection_agent import ReflectionAgent, ReflectionResult
from rag_system.agents.tool_agent import ToolAgent


class TestQueryAnalysisAgent:
    def test_analysis_defaults(self):
        analysis = QueryAnalysis(original_query="test")
        assert analysis.needs_retrieval is True
        assert analysis.query_type == "factual"
        assert analysis.complexity == "simple"

    def test_analyze_with_mock_llm(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"needs_retrieval": true, "query_type": "factual", "complexity": "simple", "rewritten_query": "test query"}'
        mock_llm.invoke.return_value = mock_response

        agent = QueryAnalysisAgent(llm=mock_llm)
        result = agent.analyze("test query")
        assert result.needs_retrieval is True
        assert result.query_type == "factual"

    def test_analyze_fallback_on_error(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")

        agent = QueryAnalysisAgent(llm=mock_llm)
        result = agent.analyze("test")
        # Should return defaults on error
        assert result.needs_retrieval is True
        assert result.original_query == "test"

    def test_extract_json(self):
        text = 'Some text {"key": "value"} more text'
        assert QueryAnalysisAgent._extract_json(text) == '{"key": "value"}'

    def test_extract_json_no_json(self):
        assert QueryAnalysisAgent._extract_json("no json here") == "no json here"


class TestReasoningAgent:
    def test_reason_no_documents(self):
        mock_llm = MagicMock()
        agent = ReasoningAgent(llm=mock_llm)
        result = agent.reason("query", [])
        assert "don't have enough context" in result

    def test_format_context(self):
        from langchain_core.documents import Document

        mock_llm = MagicMock()
        agent = ReasoningAgent(llm=mock_llm)

        docs = [
            Document(
                page_content="Test content",
                metadata={"source": "test.pdf", "page": 1},
            )
        ]
        context = agent._format_context(docs)
        assert "Source 1" in context
        assert "test.pdf" in context
        assert "Test content" in context


class TestToolAgent:
    def test_calculator(self):
        agent = ToolAgent()
        result = agent.execute("calculator", expression="2 + 3")
        assert result == "5"

    def test_calculator_complex(self):
        agent = ToolAgent()
        result = agent.execute("calculator", expression="sqrt(16)")
        assert result == "4.0"

    def test_calculator_unsafe(self):
        agent = ToolAgent()
        result = agent.execute("calculator", expression="__import__('os')")
        assert "Unsafe" in result or "error" in result.lower()

    def test_datetime(self):
        agent = ToolAgent()
        result = agent.execute("datetime")
        assert "T" in result  # ISO format contains T

    def test_unknown_tool(self):
        agent = ToolAgent()
        result = agent.execute("nonexistent")
        assert "not found" in result

    def test_register_tool(self):
        agent = ToolAgent()
        agent.register_tool("greet", lambda name="": f"Hello {name}")
        result = agent.execute("greet", name="World")
        assert result == "Hello World"

    def test_list_tools(self):
        agent = ToolAgent()
        tools = agent.list_tools()
        assert "calculator" in tools
        assert "datetime" in tools


class TestReflectionAgent:
    def test_reflection_result_defaults(self):
        result = ReflectionResult()
        assert result.score == 0.0
        assert result.is_faithful is True
        assert result.has_hallucination is False
        assert result.needs_improvement is False
        assert result.improved_answer is None

    def test_reflect_with_mock_llm(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"score": 0.9, "is_faithful": true, "has_hallucination": false, "feedback": "Good answer", "needs_improvement": false}'
        mock_llm.invoke.return_value = mock_response

        agent = ReflectionAgent(llm=mock_llm)
        result = agent.reflect("question", "context", "answer")
        assert result.score == 0.9
        assert result.is_faithful is True

    def test_reflect_fallback_on_error(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Error")

        agent = ReflectionAgent(llm=mock_llm)
        result = agent.reflect("q", "c", "a")
        # Should return defaults
        assert result.score == 0.0
