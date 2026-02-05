"""
LLM-based reranker
Uses LLM to score relevance of documents to query
"""
from typing import List, Dict, Any
import json
from loguru import logger
from openai import OpenAI

from ragapp.rerankers.base import BaseReranker
from ragapp.pipeline.types import Document
from ragapp.config import get_config


class LLMReranker(BaseReranker):
    """
    LLM-based reranker using OpenAI API
    Prompts LLM to score document relevance
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize LLM reranker
        
        Args:
            api_key: OpenAI API key (uses config if None)
            model: Model name (uses config if None)
        """
        config = get_config()
        
        self.api_key = api_key or config.llm_api_key
        self.model = model or config.llm_model
        
        if not self.api_key or self.api_key == "":
            raise ValueError("LLM API key not configured. Set LLM_API_KEY in .env.local")
        
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"LLMReranker initialized with model: {self.model}")
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 8
    ) -> List[Document]:
        """
        Rerank documents using LLM
        
        Args:
            query: User query
            documents: Documents to rerank
            top_k: Number of top documents to return
            
        Returns:
            Reranked documents
        """
        logger.info(f"🔄 Reranking {len(documents)} documents with LLM...")
        logger.info(f"Target top_k: {top_k}")
        
        if len(documents) == 0:
            return []
        
        # Score each document
        scored_docs = []
        
        for idx, doc in enumerate(documents):
            try:
                score = self._score_document(query, doc.content)
                
                # Create new document with updated score
                reranked_doc = Document(
                    content=doc.content,
                    metadata={
                        **doc.metadata,
                        'original_score': doc.score,
                        'rerank_score': score,
                        'original_rank': doc.metadata.get('rank', idx + 1)
                    },
                    score=score
                )
                scored_docs.append(reranked_doc)
                
            except Exception as e:
                logger.warning(f"Failed to score document {idx}: {e}")
                # Keep original score on error
                scored_docs.append(doc)
        
        # Sort by new score
        reranked = sorted(scored_docs, key=lambda d: d.score, reverse=True)
        
        # Update ranks
        for rank, doc in enumerate(reranked[:top_k], start=1):
            doc.metadata['rank'] = rank
        
        logger.info(f"✅ Reranking complete, returning top {top_k}")
        
        return reranked[:top_k]
    
    def _score_document(self, query: str, document: str) -> float:
        """
        Score a single document's relevance to query
        
        Args:
            query: User query
            document: Document content
            
        Returns:
            Relevance score (0-1)
        """
        # Truncate document to avoid token limits
        doc_preview = document[:1000]
        
        prompt = f"""다음 문서가 주어진 질문에 얼마나 관련이 있는지 0에서 100 사이의 점수로 평가하세요.

질문: {query}

문서: {doc_preview}

점수만 숫자로 답하세요 (0-100):"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a relevance scoring assistant. Only output a number between 0-100."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            
            # Extract number
            import re
            numbers = re.findall(r'\d+', score_text)
            if numbers:
                score = float(numbers[0]) / 100.0  # Normalize to 0-1
                return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            else:
                logger.warning(f"Could not parse score: {score_text}")
                return 0.5  # Default score
                
        except Exception as e:
            logger.error(f"LLM scoring failed: {e}")
            return 0.5  # Default score on error
