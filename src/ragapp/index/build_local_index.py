"""
Build local search index from chunks
Creates FAISS (dense) and BM25 (sparse) indices
"""
from pathlib import Path
import json
from typing import List, Dict, Any
import numpy as np
import faiss
from loguru import logger

from ragapp.embeddings.bge import BGEEmbedding
from ragapp.index.store import IndexStore


def tokenize_for_bm25(text: str) -> List[str]:
    """
    Simple tokenization for BM25
    Splits on whitespace and lowercases
    """
    return text.lower().split()


def build_local_index(
    chunks_file: Path,
    output_dir: Path,
    embedding_model: str = "BAAI/bge-m3",
    batch_size: int = 32
) -> Dict[str, Any]:
    """
    Build local hybrid index from chunks
    
    Args:
        chunks_file: Path to chunks.jsonl
        output_dir: Output directory for index
        embedding_model: BGE model name
        batch_size: Batch size for embedding
        
    Returns:
        Index metadata
    """
    logger.info("=" * 60)
    logger.info("Building Local Hybrid Index")
    logger.info("=" * 60)
    logger.info(f"Input: {chunks_file}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Embedding model: {embedding_model}")
    
    # Load chunks
    logger.info("\n📥 Loading chunks...")
    chunks = []
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
    
    logger.info(f"Loaded {len(chunks)} chunks")
    
    if len(chunks) == 0:
        raise ValueError("No chunks found in input file")
    
    # Extract texts
    texts = [chunk['content'] for chunk in chunks]
    
    # Initialize embedding model
    logger.info("\n🤖 Initializing BGE embedding model...")
    embedder = BGEEmbedding(model_name=embedding_model)
    
    # Create dense vectors (FAISS)
    logger.info("\n📊 Creating dense embeddings (FAISS)...")
    embeddings = embedder.embed_documents(texts, batch_size=batch_size)
    
    # Build FAISS index
    dimension = embeddings.shape[1]
    logger.info(f"Building FAISS index (dimension={dimension})...")
    
    # Use IndexFlatIP for cosine similarity (with normalized vectors)
    faiss_index = faiss.IndexFlatIP(dimension)
    faiss_index.add(embeddings.astype(np.float32))
    
    logger.info(f"✅ FAISS index built: {faiss_index.ntotal} vectors")
    
    # Create sparse index (BM25)
    logger.info("\n📝 Tokenizing for BM25...")
    bm25_corpus = [tokenize_for_bm25(text) for text in texts]
    logger.info(f"✅ BM25 corpus prepared: {len(bm25_corpus)} documents")
    
    # Save index
    logger.info("\n💾 Saving index...")
    store = IndexStore(output_dir)
    
    metadata = {
        "embedding_model": embedding_model,
        "embedding_dimension": dimension,
        "num_chunks": len(chunks),
        "chunks_file": str(chunks_file)
    }
    
    store.save(
        faiss_index=faiss_index,
        bm25_corpus=bm25_corpus,
        chunks=chunks,
        metadata=metadata
    )
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Index building complete!")
    logger.info("=" * 60)
    logger.info(f"Total chunks indexed: {len(chunks)}")
    logger.info(f"FAISS vectors: {faiss_index.ntotal}")
    logger.info(f"BM25 documents: {len(bm25_corpus)}")
    logger.info(f"Index location: {output_dir}")
    
    return metadata
