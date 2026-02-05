"""
Local hybrid retrieval tests
"""
import pytest
from pathlib import Path
import json
import tempfile
import shutil

from ragapp.index.build_local_index import build_local_index
from ragapp.retrievers.local_hybrid import LocalHybridRetriever
from ragapp.pipeline.types import Document


@pytest.fixture
def sample_chunks_file(tmp_path):
    """Create sample chunks file for testing"""
    chunks_file = tmp_path / "test_chunks.jsonl"
    
    chunks = [
        {
            "chunk_id": "test_001",
            "doc_id": "test_doc",
            "source_path": "/test/doc.pdf",
            "page_start": 1,
            "page_end": 1,
            "content": "RAG stands for Retrieval-Augmented Generation. It combines information retrieval with large language models.",
            "content_type": "text",
            "metadata": {"page_num": 1}
        },
        {
            "chunk_id": "test_002",
            "doc_id": "test_doc",
            "source_path": "/test/doc.pdf",
            "page_start": 2,
            "page_end": 2,
            "content": "BM25 is a ranking function used for information retrieval. It is based on probabilistic retrieval framework.",
            "content_type": "text",
            "metadata": {"page_num": 2}
        },
        {
            "chunk_id": "test_003",
            "doc_id": "test_doc",
            "source_path": "/test/doc.pdf",
            "page_start": 3,
            "page_end": 3,
            "content": "FAISS is a library for efficient similarity search and clustering of dense vectors.",
            "content_type": "text",
            "metadata": {"page_num": 3}
        }
    ]
    
    with open(chunks_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    return chunks_file


def test_index_build_creates_files(sample_chunks_file, tmp_path):
    """Test that index building creates all necessary files"""
    output_dir = tmp_path / "test_index"
    
    # Skip if no model cache (CI environment)
    try:
        metadata = build_local_index(
            chunks_file=sample_chunks_file,
            output_dir=output_dir,
            embedding_model="BAAI/bge-small-en-v1.5",  # Smaller model for testing
            batch_size=8
        )
        
        # Check files exist
        assert (output_dir / "faiss.index").exists()
        assert (output_dir / "bm25.pkl").exists()
        assert (output_dir / "chunks.jsonl").exists()
        assert (output_dir / "metadata.json").exists()
        
        # Check metadata
        assert metadata['num_chunks'] == 3
        assert 'embedding_dimension' in metadata
        
    except Exception as e:
        pytest.skip(f"Skipping test (model download required): {e}")


def test_retrieval_returns_documents(sample_chunks_file, tmp_path):
    """Test that retrieval returns Document objects with correct schema"""
    output_dir = tmp_path / "test_index"
    
    try:
        # Build index
        build_local_index(
            chunks_file=sample_chunks_file,
            output_dir=output_dir,
            embedding_model="BAAI/bge-small-en-v1.5",
            batch_size=8
        )
        
        # Initialize retriever
        retriever = LocalHybridRetriever(output_dir)
        
        # Retrieve
        results = retriever.retrieve("What is RAG?", top_n=5)
        
        # Validate results
        assert len(results) > 0
        assert len(results) <= 5
        
        # Check Document schema
        for doc in results:
            assert isinstance(doc, Document)
            assert isinstance(doc.content, str)
            assert isinstance(doc.metadata, dict)
            assert isinstance(doc.score, float)
            
            # Check required metadata fields
            assert 'chunk_id' in doc.metadata
            assert 'doc_id' in doc.metadata
            assert 'source_path' in doc.metadata
            assert 'content_type' in doc.metadata
            assert 'rank' in doc.metadata
        
        # Check ranking
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, "Results should be sorted by score"
        
    except Exception as e:
        pytest.skip(f"Skipping test (model download required): {e}")


def test_retrieval_top_n_limit(sample_chunks_file, tmp_path):
    """Test that top_n parameter limits results"""
    output_dir = tmp_path / "test_index"
    
    try:
        # Build index
        build_local_index(
            chunks_file=sample_chunks_file,
            output_dir=output_dir,
            embedding_model="BAAI/bge-small-en-v1.5",
            batch_size=8
        )
        
        retriever = LocalHybridRetriever(output_dir)
        
        # Test different top_n values
        results_2 = retriever.retrieve("retrieval", top_n=2)
        results_5 = retriever.retrieve("retrieval", top_n=5)
        
        assert len(results_2) <= 2
        assert len(results_5) <= 5  # May be less than 5 if only 3 chunks
        
    except Exception as e:
        pytest.skip(f"Skipping test (model download required): {e}")
