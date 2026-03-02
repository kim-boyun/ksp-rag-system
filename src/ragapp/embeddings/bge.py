"""
BGE (BAAI General Embedding) model wrapper
Supports multilingual embeddings with caching
"""
import os
import re
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger


def _normalize_text_for_embedding(text: str) -> str:
    """임베딩 전 공백·줄바꿈 정규화."""
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _detect_device() -> str:
    """CUDA → MPS(Apple Silicon) → CPU 순으로 최적 디바이스 자동 감지."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


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
            device: Device to use (None=auto-detect: cuda > mps > cpu)
        """
        self.model_name = model_name

        if device is None:
            device = _detect_device()

        logger.info(f"Loading BGE model: {model_name}")
        logger.info(f"Device: {device}")
        logger.info("This may take a few minutes on first run (downloading model)...")
        
        # Load model (cached to ~/.cache/huggingface)
        self.model = SentenceTransformer(model_name, device=device)

        # Limit maximum sequence length for stability on MPS / limited-memory devices.
        # Can be overridden with env BGE_MAX_SEQ_LENGTH (tokens).
        try:
            max_seq_default = 1024
            max_seq_env = os.getenv("BGE_MAX_SEQ_LENGTH")
            max_seq = int(max_seq_env) if max_seq_env is not None else max_seq_default
            self.model.max_seq_length = max_seq
            logger.info(f"Max sequence length set to: {self.model.max_seq_length}")
        except Exception as e:
            logger.warning(f"Failed to set max_seq_length on BGE model: {e}")
        
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
        text = _normalize_text_for_embedding(text)
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
        Embed multiple documents.
        임베딩 전에 공백·줄바꿈 정규화 적용.
        """
        normalized = [_normalize_text_for_embedding(t) for t in texts]
        logger.info(f"Embedding {len(normalized)} documents...")

        # Robust embedding with automatic batch size backoff on memory errors (MPS / CUDA).
        current_batch_size = max(1, batch_size)

        while True:
            try:
                embeddings = self.model.encode(
                    normalized,
                    batch_size=current_batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=True
                )
                logger.info(f"✅ Embedded {len(normalized)} documents (batch_size={current_batch_size})")
                return embeddings
            except RuntimeError as e:
                msg = str(e)
                # Handle memory-related errors by reducing batch size
                if (
                    "out of memory" in msg.lower()
                    or "mps backend out of memory" in msg.lower()
                    or "invalid buffer size" in msg.lower()
                ):
                    if current_batch_size == 1:
                        logger.error("Memory error even with batch_size=1; giving up.")
                        raise
                    new_batch_size = max(1, current_batch_size // 2)
                    logger.warning(
                        f"Memory error during embedding (batch_size={current_batch_size}): {e}. "
                        f"Retrying with smaller batch_size={new_batch_size}."
                    )
                    current_batch_size = new_batch_size

                    # Try to free device cache between retries (best-effort).
                    try:
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                            torch.mps.empty_cache()
                    except Exception:
                        pass
                else:
                    # Non-memory related error: re-raise immediately
                    raise
    
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
