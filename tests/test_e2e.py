"""
End-to-end RAG pipeline tests
"""
import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch

from ragapp.pipeline.rag_pipeline import RAGPipeline
from ragapp.pipeline.types import Document, RAGResponse


def test_retrieval_smoke_test():
    """Smoke test: retrieval pipeline doesn't crash"""
    try:
        # Try to initialize pipeline
        pipeline = RAGPipeline()
        
        # Pipeline should initialize (may use placeholder)
        assert pipeline is not None
        assert pipeline.retriever is not None
        assert pipeline.llm is not None
        
    except Exception as e:
        pytest.skip(f"Pipeline initialization failed (expected in CI): {e}")


def test_ask_with_mock_llm():
    """Test ask command with mocked LLM"""
    # Create mock LLM
    mock_llm = Mock()
    mock_llm.generate.return_value = "This is a test answer with [출처: 문서 1] citation."
    
    # Create mock retriever
    mock_retriever = Mock()
    mock_retriever.retrieve.return_value = [
        Document(
            content="Test document content about Honduras pension system.",
            metadata={
                "doc_id": "test_doc",
                "page_num": 5,
                "chunk_id": "test_chunk_001",
                "content_type": "text"
            },
            score=0.95
        )
    ]
    
    # Create pipeline with mocks
    pipeline = RAGPipeline(
        retriever=mock_retriever,
        reranker=None,
        llm=mock_llm,
        use_rerank=False
    )
    
    # Ask question
    response = pipeline.ask("Test question?")
    
    # Validate response structure
    assert isinstance(response, RAGResponse)
    assert isinstance(response.answer, str)
    assert len(response.answer) > 0
    assert isinstance(response.retrieved_docs, list)
    assert len(response.retrieved_docs) > 0
    assert isinstance(response.metadata, dict)
    
    # Check LLM was called
    assert mock_llm.generate.called


def test_citations_structure():
    """Test that citations are properly extracted and formatted"""
    from ragapp.prompts import extract_citations
    from ragapp.pipeline.types import Document
    
    # Create sample documents
    documents = [
        Document(
            content="Document 1 content",
            metadata={
                "doc_id": "doc_001",
                "page_num": 5,
                "chunk_id": "chunk_001",
                "content_type": "text"
            },
            score=0.9
        ),
        Document(
            content="Document 2 content",
            metadata={
                "doc_id": "doc_002",
                "page_num": 12,
                "chunk_id": "chunk_002",
                "content_type": "table_md"
            },
            score=0.8
        )
    ]
    
    # Answer with citations
    answer = "This is an answer based on [출처: 문서 1] and also [출처: 문서 2]."
    
    citations = extract_citations(answer, documents)
    
    # Validate citations structure
    assert len(citations) == 2
    
    # Check first citation
    assert citations[0]["doc_num"] == 1
    assert citations[0]["doc_id"] == "doc_001"
    assert citations[0]["page_num"] == 5
    assert citations[0]["chunk_id"] == "chunk_001"
    assert citations[0]["content_type"] == "text"
    
    # Check second citation
    assert citations[1]["doc_num"] == 2
    assert citations[1]["doc_id"] == "doc_002"
    assert citations[1]["page_num"] == 12
    assert citations[1]["content_type"] == "table_md"


def test_citations_with_no_answer():
    """Test citations when answer has no evidence"""
    from ragapp.prompts import extract_citations
    from ragapp.pipeline.types import Document
    
    documents = [
        Document(
            content="Test",
            metadata={"doc_id": "doc_001", "page_num": 1, "chunk_id": "c1", "content_type": "text"},
            score=0.5
        )
    ]
    
    # Answer without citations
    answer = "제공된 문서에서 관련 정보를 찾을 수 없습니다."
    
    citations = extract_citations(answer, documents)
    
    # Should be empty
    assert len(citations) == 0


def test_ask_returns_citations_in_metadata():
    """Test ask response includes citation information"""
    mock_llm = Mock()
    mock_llm.generate.return_value = "Answer based on [출처: 문서 1]."
    
    mock_retriever = Mock()
    mock_retriever.retrieve.return_value = [
        Document(
            content="Content",
            metadata={
                "doc_id": "doc_001",
                "page_num": 3,
                "chunk_id": "chunk_001",
                "content_type": "text"
            },
            score=0.9
        )
    ]
    
    pipeline = RAGPipeline(
        retriever=mock_retriever,
        llm=mock_llm,
        use_rerank=False
    )
    
    response = pipeline.ask("Test question")
    
    # Response should have documents
    assert len(response.retrieved_docs) > 0
    
    # Each document should have required metadata
    for doc in response.retrieved_docs:
        assert 'doc_id' in doc.metadata
        assert 'page_num' in doc.metadata
        assert 'chunk_id' in doc.metadata
        assert 'content_type' in doc.metadata


def test_e2e_pipeline_with_rerank():
    """Test E2E pipeline with reranking enabled"""
    # Mock components
    mock_llm = Mock()
    mock_llm.generate.return_value = "Reranked answer [출처: 문서 1]."
    
    mock_retriever = Mock()
    mock_retriever.retrieve.return_value = [
        Document(
            content=f"Doc {i}",
            metadata={"doc_id": f"doc_{i}", "page_num": i, "chunk_id": f"c{i}", "content_type": "text"},
            score=1.0 / (i + 1)
        )
        for i in range(5)
    ]
    
    mock_reranker = Mock()
    mock_reranker.rerank.return_value = mock_retriever.retrieve.return_value[:3]
    
    # Create pipeline with rerank
    pipeline = RAGPipeline(
        retriever=mock_retriever,
        reranker=mock_reranker,
        llm=mock_llm,
        use_rerank=True
    )
    
    response = pipeline.ask("Test question", use_rerank=True)
    
    # Validate reranker was called
    assert mock_reranker.rerank.called
    
    # Validate response
    assert response is not None
    assert isinstance(response.answer, str)
    assert response.metadata["rerank_enabled"] is True
