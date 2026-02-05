"""
Pipeline tests
"""
import pytest
from ragapp.pipeline.rag_pipeline import RAGPipeline
from ragapp.pipeline.types import Document, RAGResponse


def test_pipeline_placeholder():
    """Test RAG pipeline with placeholder components"""
    pipeline = RAGPipeline()
    
    # Test query
    response = pipeline.ask("What is RAG?")
    
    # Validate response structure
    assert isinstance(response, RAGResponse)
    assert isinstance(response.answer, str)
    assert len(response.answer) > 0
    assert isinstance(response.retrieved_docs, list)
    assert len(response.retrieved_docs) > 0
    assert isinstance(response.metadata, dict)
    
    # Validate retrieved documents
    for doc in response.retrieved_docs:
        assert isinstance(doc, Document)
        assert isinstance(doc.content, str)
        assert isinstance(doc.metadata, dict)
        assert doc.score >= 0.0


def test_pipeline_retrieval():
    """Test retrieval step"""
    pipeline = RAGPipeline()
    
    docs = pipeline.retriever.retrieve("test query", top_k=3)
    
    assert len(docs) == 3
    assert all(isinstance(doc, Document) for doc in docs)


def test_pipeline_reranking():
    """Test reranking step"""
    pipeline = RAGPipeline()
    
    # Create sample documents
    docs = [
        Document(content=f"Document {i}", metadata={"id": i}, score=float(i))
        for i in range(5)
    ]
    
    reranked = pipeline.reranker.rerank("test query", docs, top_k=3)
    
    assert len(reranked) == 3


def test_pipeline_generation():
    """Test generation step"""
    pipeline = RAGPipeline()
    
    answer = pipeline.llm.generate("Test prompt", max_tokens=100)
    
    assert isinstance(answer, str)
    assert len(answer) > 0
