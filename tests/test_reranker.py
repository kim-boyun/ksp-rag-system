"""
Reranker tests
"""
import pytest
from unittest.mock import Mock, patch

from ragapp.rerankers.base import NoOpReranker
from ragapp.rerankers.llm_reranker import LLMReranker
from ragapp.pipeline.types import Document


def test_noop_reranker_returns_top_k():
    """Test NoOpReranker returns exactly top_k documents"""
    reranker = NoOpReranker()
    
    # Create 10 documents
    documents = [
        Document(
            content=f"Document {i}",
            metadata={"id": i},
            score=1.0 / (i + 1)
        )
        for i in range(10)
    ]
    
    # Rerank with top_k=5
    reranked = reranker.rerank("test query", documents, top_k=5)
    
    assert len(reranked) == 5
    assert reranked[0].metadata["id"] == 0
    assert reranked[4].metadata["id"] == 4


def test_reranker_preserves_metadata():
    """Test reranker preserves original document metadata"""
    reranker = NoOpReranker()
    
    documents = [
        Document(
            content="Test content",
            metadata={"chunk_id": "chunk_001", "doc_id": "doc_001"},
            score=0.8
        )
    ]
    
    reranked = reranker.rerank("query", documents, top_k=1)
    
    assert reranked[0].metadata["chunk_id"] == "chunk_001"
    assert reranked[0].metadata["doc_id"] == "doc_001"


def test_llm_reranker_returns_top_k():
    """Test LLM reranker returns exactly top_k documents"""
    # Mock OpenAI client
    with patch('ragapp.rerankers.llm_reranker.OpenAI') as mock_openai:
        # Mock response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "85"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Create reranker
        reranker = LLMReranker(api_key="test-key")
        
        # Create documents
        documents = [
            Document(
                content=f"Document {i} content",
                metadata={"id": i},
                score=1.0 / (i + 1)
            )
            for i in range(10)
        ]
        
        # Rerank
        reranked = reranker.rerank("test query", documents, top_k=5)
        
        # Should return exactly 5
        assert len(reranked) == 5


def test_llm_reranker_updates_scores():
    """Test LLM reranker updates document scores"""
    with patch('ragapp.rerankers.llm_reranker.OpenAI') as mock_openai:
        # Mock different scores for each document
        mock_client = Mock()
        scores = ["90", "50", "75"]
        call_count = [0]
        
        def mock_create(*args, **kwargs):
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = scores[call_count[0] % len(scores)]
            call_count[0] += 1
            return mock_response
        
        mock_client.chat.completions.create.side_effect = mock_create
        mock_openai.return_value = mock_client
        
        reranker = LLMReranker(api_key="test-key")
        
        documents = [
            Document(content=f"Doc {i}", metadata={"id": i}, score=0.5)
            for i in range(3)
        ]
        
        reranked = reranker.rerank("query", documents, top_k=3)
        
        # Check scores are updated and stored
        assert reranked[0].score > 0.0
        assert 'rerank_score' in reranked[0].metadata
        assert 'original_score' in reranked[0].metadata


def test_reranker_handles_empty_list():
    """Test reranker handles empty document list"""
    reranker = NoOpReranker()
    
    reranked = reranker.rerank("query", [], top_k=5)
    
    assert len(reranked) == 0


def test_reranker_top_k_larger_than_docs():
    """Test reranker when top_k > number of documents"""
    reranker = NoOpReranker()
    
    documents = [
        Document(content=f"Doc {i}", metadata={"id": i}, score=1.0)
        for i in range(3)
    ]
    
    # Request 10 but only 3 available
    reranked = reranker.rerank("query", documents, top_k=10)
    
    # Should return all 3
    assert len(reranked) == 3
