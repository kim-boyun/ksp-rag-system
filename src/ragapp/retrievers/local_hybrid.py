"""
Local hybrid retriever using BM25 + FAISS with RRF fusion
"""
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi
from loguru import logger

from ragapp.embeddings.bge import BGEEmbedding
from ragapp.index.store import IndexStore
from ragapp.pipeline.types import Document


def reciprocal_rank_fusion(
    bm25_results: List[tuple[int, float]],
    faiss_results: List[tuple[int, float]],
    k: int = 60
) -> List[tuple[int, float]]:
    """
    Reciprocal Rank Fusion (RRF)
    Combines BM25 and FAISS results
    
    Args:
        bm25_results: List of (doc_idx, score) from BM25
        faiss_results: List of (doc_idx, score) from FAISS
        k: RRF constant (default: 60)
        
    Returns:
        Fused results sorted by RRF score
    """
    rrf_scores: Dict[int, float] = {}
    
    # Add BM25 scores
    for rank, (doc_idx, _) in enumerate(bm25_results, start=1):
        rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + 1.0 / (k + rank)
    
    # Add FAISS scores
    for rank, (doc_idx, _) in enumerate(faiss_results, start=1):
        rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + 1.0 / (k + rank)
    
    # Sort by RRF score
    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    return fused


class LocalHybridRetriever:
    """
    Local hybrid retriever using BM25 + FAISS + RRF
    """
    
    def __init__(self, index_dir: Path):
        """
        Initialize retriever from index directory
        
        Args:
            index_dir: Directory containing index files
        """
        logger.info(f"Initializing LocalHybridRetriever from {index_dir}")
        
        self.index_dir = Path(index_dir)
        
        # Load index
        store = IndexStore(self.index_dir)
        
        if not store.exists():
            raise FileNotFoundError(f"Index not found in {index_dir}. Run 'ragapp index' first.")
        
        self.faiss_index, self.bm25_corpus, self.chunks, self.metadata = store.load()
        
        # Initialize BM25
        logger.info("Initializing BM25...")
        self.bm25 = BM25Okapi(self.bm25_corpus)
        
        # Initialize embedding model
        embedding_model = self.metadata.get('embedding_model', 'BAAI/bge-m3')
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedder = BGEEmbedding(model_name=embedding_model)
        
        logger.info(f"✅ LocalHybridRetriever ready!")
        logger.info(f"Indexed chunks: {len(self.chunks)}")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 20,
        bm25_weight: float = 0.5,
        faiss_weight: float = 0.5
    ) -> List[Document]:
        """
        Retrieve documents using hybrid search
        
        Args:
            query: Search query
            top_k: Number of results to return
            bm25_weight: Weight for BM25 (not used in RRF, kept for API)
            faiss_weight: Weight for FAISS (not used in RRF, kept for API)
            
        Returns:
            List of retrieved documents
        """
        logger.info(f"🔍 Retrieving: {query}")
        logger.info(f"Top K: {top_k}")
        
        # Tokenize query for BM25
        query_tokens = query.lower().split()
        
        # BM25 search
        logger.info("Searching with BM25...")
        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_top_indices = np.argsort(bm25_scores)[::-1][:top_k * 2]  # Get more for fusion
        bm25_results = [(int(idx), float(bm25_scores[idx])) for idx in bm25_top_indices]
        
        # FAISS search
        logger.info("Searching with FAISS...")
        query_embedding = self.embedder.embed_query(query)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        
        faiss_scores, faiss_indices = self.faiss_index.search(query_embedding, top_k * 2)
        faiss_results = [(int(idx), float(score)) for idx, score in zip(faiss_indices[0], faiss_scores[0])]
        
        # RRF fusion
        logger.info("Fusing results with RRF...")
        fused_results = reciprocal_rank_fusion(bm25_results, faiss_results)
        
        # Take top K
        top_results = fused_results[:top_k]
        
        # Build Document objects
        documents = []
        for rank, (doc_idx, rrf_score) in enumerate(top_results, start=1):
            chunk = self.chunks[doc_idx]
            
            doc = Document(
                content=chunk['content'],
                metadata={
                    **chunk['metadata'],
                    'chunk_id': chunk['chunk_id'],
                    'doc_id': chunk['doc_id'],
                    'source_path': chunk['source_path'],
                    'content_type': chunk['content_type'],
                    'rank': rank
                },
                score=rrf_score
            )
            documents.append(doc)
        
        logger.info(f"✅ Retrieved {len(documents)} documents")
        
        return documents
    
    def get_chunk_by_id(self, chunk_id: str) -> Dict[str, Any] | None:
        """Get chunk by ID"""
        for chunk in self.chunks:
            if chunk['chunk_id'] == chunk_id:
                return chunk
        return None
