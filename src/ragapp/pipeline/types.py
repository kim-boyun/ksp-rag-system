"""
Pipeline component interfaces (Protocol-based)
"""
from typing import Protocol, List, Any
from dataclasses import dataclass


@dataclass
class Document:
    """Document with content and metadata"""
    content: str
    metadata: dict[str, Any]
    score: float = 0.0
    
    def __repr__(self) -> str:
        return f"Document(score={self.score:.4f}, content={self.content[:50]}...)"


@dataclass
class RAGResponse:
    """RAG pipeline response"""
    answer: str
    retrieved_docs: List[Document]
    metadata: dict[str, Any]


class Retriever(Protocol):
    """
    Retriever interface
    Implementations: BM25Retriever, FAISSRetriever, ElasticRetriever
    """
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Search query
            top_k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents with scores
        """
        ...


class Reranker(Protocol):
    """
    Reranker interface
    Implementations: CrossEncoderReranker, NoOpReranker
    """
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 3) -> List[Document]:
        """
        Rerank documents based on query relevance
        
        Args:
            query: Search query
            documents: Documents to rerank
            top_k: Number of top documents to return
            
        Returns:
            Reranked documents
        """
        ...


class LLMClient(Protocol):
    """
    LLM client interface
    Implementations: OpenAIClient, vLLMClient
    """
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Generate text using LLM
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        ...
