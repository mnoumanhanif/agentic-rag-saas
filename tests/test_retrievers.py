"""Tests for the retrievers module."""

from unittest.mock import MagicMock, create_autospec

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from rag_system.retrievers.context_compressor import ContextCompressor
from rag_system.retrievers.dense_retriever import DenseRetriever
from rag_system.retrievers.hybrid_retriever import HybridRetriever
from rag_system.retrievers.reranker import Reranker
from rag_system.retrievers.sparse_retriever import SparseRetriever


def _mock_vector_store():
    """Create a mock VectorStore that passes Pydantic validation."""
    return create_autospec(VectorStore, instance=True)


class TestContextCompressor:
    def test_compress_basic(self):
        compressor = ContextCompressor(max_tokens_per_doc=50)
        docs = [
            Document(
                page_content="Python is great for data science. Java is used for enterprise. "
                "Python has many libraries for machine learning.",
                metadata={"source": "test"},
            )
        ]
        result = compressor.compress("Python machine learning", docs)
        assert len(result) == 1
        assert result[0].metadata.get("compressed") is True

    def test_compress_empty(self):
        compressor = ContextCompressor()
        assert compressor.compress("query", []) == []

    def test_preserves_metadata(self):
        compressor = ContextCompressor()
        docs = [
            Document(
                page_content="Some content about testing.",
                metadata={"source": "file.pdf", "page": 1},
            )
        ]
        result = compressor.compress("testing", docs)
        assert result[0].metadata["source"] == "file.pdf"
        assert result[0].metadata["page"] == 1


class TestSparseRetriever:
    def test_bm25_search(self):
        docs = [
            Document(page_content="Python programming language", metadata={}),
            Document(page_content="Java enterprise applications", metadata={}),
            Document(page_content="Python machine learning", metadata={}),
        ]
        retriever = SparseRetriever(documents=docs, search_k=2)
        results = retriever.invoke("Python")
        assert len(results) == 2
        assert all("python" in r.page_content.lower() for r in results)

    def test_empty_documents(self):
        retriever = SparseRetriever(documents=[], search_k=2)
        results = retriever.invoke("test query")
        assert results == []

    def test_no_matching_terms(self):
        docs = [
            Document(page_content="alpha beta gamma", metadata={}),
        ]
        retriever = SparseRetriever(documents=docs, search_k=2)
        results = retriever.invoke("delta epsilon")
        assert results == []


class TestDenseRetriever:
    def test_from_vector_store(self):
        mock_store = _mock_vector_store()
        mock_store.similarity_search.return_value = [
            Document(page_content="result", metadata={})
        ]
        retriever = DenseRetriever.from_vector_store(mock_store, search_k=2)
        results = retriever.invoke("test query")
        assert len(results) == 1
        mock_store.similarity_search.assert_called_once()


class TestHybridRetriever:
    def test_reciprocal_rank_fusion(self):
        mock_store = _mock_vector_store()
        doc1 = Document(page_content="Document about Python programming", metadata={})
        doc2 = Document(page_content="Document about Java development", metadata={})

        retriever = HybridRetriever(
            vector_store=mock_store, documents=[], search_k=4
        )
        result = retriever._reciprocal_rank_fusion([doc1, doc2], [doc2, doc1])
        assert len(result) == 2

    def test_dense_only_mode(self):
        mock_store = _mock_vector_store()
        mock_store.similarity_search.return_value = [
            Document(page_content="dense result", metadata={})
        ]
        retriever = HybridRetriever(
            vector_store=mock_store, documents=[], search_k=2
        )
        results = retriever.invoke("test")
        assert len(results) == 1


class TestReranker:
    def test_rerank_empty(self):
        reranker = Reranker()
        assert reranker.rerank("query", []) == []

    def test_rerank_no_model(self):
        reranker = Reranker(model_name="nonexistent-model")
        docs = [Document(page_content="test", metadata={})]
        # Should gracefully return original order if model can't load
        result = reranker.rerank("query", docs)
        assert len(result) == 1
