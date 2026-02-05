"""
Index storage and loading
Handles FAISS index, BM25 index, and metadata
"""
from pathlib import Path
import json
import pickle
from typing import Dict, Any, List
import numpy as np
import faiss
from loguru import logger


class IndexStore:
    """
    Manages local index storage
    Stores: FAISS index, BM25 tokenized corpus, chunk metadata
    """
    
    def __init__(self, index_dir: Path):
        """
        Initialize index store
        
        Args:
            index_dir: Directory to store index files
        """
        self.index_dir = Path(index_dir)
        self.faiss_path = self.index_dir / "faiss.index"
        self.bm25_path = self.index_dir / "bm25.pkl"
        self.metadata_path = self.index_dir / "metadata.json"
        self.chunks_path = self.index_dir / "chunks.jsonl"
    
    def save(
        self,
        faiss_index: faiss.Index,
        bm25_corpus: List[List[str]],
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ):
        """
        Save index to disk
        
        Args:
            faiss_index: FAISS index
            bm25_corpus: Tokenized corpus for BM25
            chunks: List of chunk dictionaries
            metadata: Index metadata (model name, dimensions, etc.)
        """
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving index to {self.index_dir}")
        
        # Save FAISS index
        faiss.write_index(faiss_index, str(self.faiss_path))
        logger.info(f"✅ Saved FAISS index: {self.faiss_path}")
        
        # Save BM25 corpus
        with open(self.bm25_path, 'wb') as f:
            pickle.dump(bm25_corpus, f)
        logger.info(f"✅ Saved BM25 corpus: {self.bm25_path}")
        
        # Save chunks
        with open(self.chunks_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        logger.info(f"✅ Saved {len(chunks)} chunks: {self.chunks_path}")
        
        # Save metadata
        metadata['num_chunks'] = len(chunks)
        metadata['faiss_index_size'] = faiss_index.ntotal
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved metadata: {self.metadata_path}")
        
        logger.info(f"🎉 Index saved successfully!")
    
    def load(self) -> tuple[faiss.Index, List[List[str]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Load index from disk
        
        Returns:
            Tuple of (faiss_index, bm25_corpus, chunks, metadata)
        """
        logger.info(f"Loading index from {self.index_dir}")
        
        # Load FAISS index
        if not self.faiss_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {self.faiss_path}")
        faiss_index = faiss.read_index(str(self.faiss_path))
        logger.info(f"✅ Loaded FAISS index: {faiss_index.ntotal} vectors")
        
        # Load BM25 corpus
        if not self.bm25_path.exists():
            raise FileNotFoundError(f"BM25 corpus not found: {self.bm25_path}")
        with open(self.bm25_path, 'rb') as f:
            bm25_corpus = pickle.load(f)
        logger.info(f"✅ Loaded BM25 corpus: {len(bm25_corpus)} documents")
        
        # Load chunks
        if not self.chunks_path.exists():
            raise FileNotFoundError(f"Chunks not found: {self.chunks_path}")
        chunks = []
        with open(self.chunks_path, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line))
        logger.info(f"✅ Loaded {len(chunks)} chunks")
        
        # Load metadata
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata not found: {self.metadata_path}")
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        logger.info(f"✅ Loaded metadata")
        
        logger.info(f"🎉 Index loaded successfully!")
        
        return faiss_index, bm25_corpus, chunks, metadata
    
    def exists(self) -> bool:
        """Check if index exists"""
        return (
            self.faiss_path.exists() and
            self.bm25_path.exists() and
            self.chunks_path.exists() and
            self.metadata_path.exists()
        )
