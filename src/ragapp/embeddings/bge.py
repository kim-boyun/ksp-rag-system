"""
BGE (BAAI General Embedding) model wrapper
Supports multilingual embeddings with caching
"""
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger


class BGEEmbedding:
    """
    BGE embedding model wrapper
    Default: BAAI/bge-m3 (multilingual, 1024 dim)
    """
    
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = None):
        """
        Initialize BGE embedding model
        
        Args:
            model_name: HuggingFace model name
            device: Device to use (None=auto, 'cuda', 'cpu', 'mps')
        """
        self.model_name = model_name
        
        logger.info(f"Loading BGE model: {model_name}")
        logger.info("This may take a few minutes on first run (downloading model)...")
        
        # Load model (cached to /root/.cache/huggingface)
        self.model = SentenceTransformer(model_name, device=device)
        
        # Get embedding dimension
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"✅ BGE model loaded: {model_name}")
        logger.info(f"Embedding dimension: {self.dimension}")
        logger.info(f"Device: {self.model.device}")
    
    def embed_query(self, text: str) -> np.ndarray:
        """
        Embed a single query
        
        Args:
            text: Query text
            
        Returns:
            Embedding vector (numpy array)
        """
        # For BGE models, add "Represent this sentence for searching relevant passages: "
        # to improve retrieval quality
        query_prefix = "Represent this sentence for searching relevant passages: "
        query_with_prefix = query_prefix + text
        
        embedding = self.model.encode(
            query_with_prefix,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )
        
        return embedding
    
    def embed_documents(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Embed multiple documents
        
        Args:
            texts: List of document texts
            batch_size: Batch size for encoding
            
        Returns:
            Embedding matrix (num_docs x dimension)
        """
        logger.info(f"Embedding {len(texts)} documents...")
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True
        )
        
        logger.info(f"✅ Embedded {len(texts)} documents")
        
        return embeddings
    
    def encode(self, texts: List[str] | str, **kwargs) -> np.ndarray:
        """
        Generic encode method
        
        Args:
            texts: Text or list of texts
            **kwargs: Additional arguments for model.encode
            
        Returns:
            Embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            **kwargs
        )
