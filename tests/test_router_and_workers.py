"""Tests for the router agent and worker tasks."""

from unittest.mock import MagicMock

from rag_system.agents.router_agent import RouterAgent, RoutingDecision
from rag_system.workers.tasks import JobInfo, JobStatus, get_job_info


class TestRoutingDecision:
    def test_defaults(self):
        decision = RoutingDecision()
        assert decision.use_dense_retrieval is True
        assert decision.use_sparse_retrieval is True
        assert decision.use_tools == []
        assert decision.reasoning == ""


class TestRouterAgent:
    def test_rule_based_routing_default(self):
        agent = RouterAgent(llm=None)
        decision = agent.route("What is machine learning?")
        assert decision.use_dense_retrieval is True
        assert decision.use_sparse_retrieval is True
        assert "Rule-based" in decision.reasoning

    def test_rule_based_routing_calculator(self):
        agent = RouterAgent(llm=None)
        decision = agent.route("Calculate the sum of 5 and 10")
        assert "calculator" in decision.use_tools

    def test_rule_based_routing_datetime(self):
        agent = RouterAgent(llm=None)
        decision = agent.route("What time is it today?")
        assert "datetime" in decision.use_tools

    def test_route_with_mock_llm(self):
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '{"use_dense_retrieval": true, "use_sparse_retrieval": false, "use_tools": [], "reasoning": "Semantic query"}'
        mock_llm.invoke.return_value = mock_response

        agent = RouterAgent(llm=mock_llm)
        decision = agent.route("Explain the concept of neural networks")
        assert decision.use_dense_retrieval is True
        assert decision.use_sparse_retrieval is False

    def test_route_fallback_on_error(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")

        agent = RouterAgent(llm=mock_llm)
        decision = agent.route("test query")
        # Should fall back to rule-based routing
        assert decision.use_dense_retrieval is True

    def test_extract_json(self):
        text = 'Some text {"key": "value"} more text'
        assert RouterAgent._extract_json(text) == '{"key": "value"}'


class TestJobInfo:
    def test_defaults(self):
        info = JobInfo(job_id="test-123")
        assert info.status == JobStatus.QUEUED
        assert info.message == ""
        assert info.files == []
        assert info.error is None


class TestGetJobInfo:
    def test_nonexistent_job(self):
        result = get_job_info("nonexistent-job-id-12345")
        assert result is None


class TestBatchEmbeddingSettings:
    def test_defaults(self):
        from rag_system.config.settings import BatchEmbeddingSettings

        s = BatchEmbeddingSettings()
        assert s.batch_size == 32
        assert s.show_progress is False


class TestWorkerSettings:
    def test_defaults(self):
        from rag_system.config.settings import WorkerSettings

        s = WorkerSettings()
        assert s.enabled is False
        assert s.queue_name == "default"
        assert s.job_timeout == 600
