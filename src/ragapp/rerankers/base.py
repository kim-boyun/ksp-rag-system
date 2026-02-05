"""
Base reranker interface
"""
from abc import ABC, abstractmethod
from typing import List
from ragapp.pipeline.types import Document


class BaseReranker(ABC):
    """
    Base reranker interface
    Reranks retrieved documents based on relevance to query
    """
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 8
    ) -> List[Document]:
        """
        Rerank documents by relevance to query
        
        Args:
            query: User query
            documents: Retrieved documents to rerank
            top_k: Number of top documents to return
            
        Returns:
            Reranked documents with updated scores
        """
        pass


class NoOpReranker(BaseReranker):
    """
    No-op reranker (returns documents as-is)
    Used when reranking is disabled
    """
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 8
    ) -> List[Document]:
        """Simply return top_k documents without reranking"""
        return documents[:top_k]
