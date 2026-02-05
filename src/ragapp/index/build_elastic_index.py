"""
Build Elasticsearch index from chunks
"""
import json
from pathlib import Path
from typing import List
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import track

from ragapp.embeddings.bge import BGEEmbedding
from ragapp.retrievers.elastic_retriever import ElasticHybridRetriever


console = Console()


def build_elastic_index(
    chunks_file: str,
    elastic_host: str = "localhost",
    elastic_port: int = 9200,
    index_name: str = "ksp_rag_index",
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    batch_size: int = 32,
    recreate: bool = False
):
    """
    Build Elasticsearch index from chunks
    
    Args:
        chunks_file: Path to chunks JSONL file
        elastic_host: Elasticsearch host
        elastic_port: Elasticsearch port
        index_name: Index name
        embedding_model: Embedding model
        batch_size: Batch size for embedding
        recreate: Whether to recreate index if exists
    """
    logger.info("=" * 60)
    logger.info("Building Elasticsearch Hybrid Index")
    logger.info("=" * 60)
    logger.info(f"Input: {chunks_file}")
    logger.info(f"Elasticsearch: {elastic_host}:{elastic_port}")
    logger.info(f"Index: {index_name}")
    logger.info(f"Embedding model: {embedding_model}")
    
    # Load chunks
    logger.info("\n📥 Loading chunks...")
    chunks_path = Path(chunks_file)
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")
    
    chunks = []
    with open(chunks_path, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
    
    logger.info(f"Loaded {len(chunks)} chunks")
    
    # Initialize retriever (for indexing)
    logger.info("\n🔌 Connecting to Elasticsearch...")
    retriever = ElasticHybridRetriever(
        host=elastic_host,
        port=elastic_port,
        index_name=index_name,
        embedding_model=embedding_model
    )
    
    # Create or recreate index
    if recreate and retriever.index_exists():
        logger.warning(f"Recreating index: {index_name}")
        retriever.delete_index()
    
    if not retriever.index_exists():
        logger.info(f"Creating index: {index_name}")
        embedding_dim = retriever.embedder.dimension
        retriever.create_index(embedding_dim=embedding_dim)
    else:
        logger.info(f"Index already exists: {index_name}")
    
    # Generate embeddings
    logger.info("\n🤖 Generating embeddings...")
    texts = [chunk.get("content", "") for chunk in chunks]
    
    console.print(f"Embedding {len(texts)} documents...")
    embeddings = retriever.embedder.embed_documents(
        texts,
        batch_size=batch_size
    )
    
    # Bulk index
    logger.info("\n📤 Indexing to Elasticsearch...")
    with console.status("[bold green]Indexing documents..."):
        retriever.bulk_index(chunks, embeddings)
    
    logger.info("\n🎉 Elasticsearch index built successfully!")
    logger.info(f"Index: {index_name}")
    logger.info(f"Total chunks: {len(chunks)}")
    
    # Print summary
    console.print(Panel.fit(
        f"[bold green]✅ Index built successfully![/bold green]\n\n"
        f"[cyan]Index:[/cyan] {index_name}\n"
        f"[cyan]Chunks:[/cyan] {len(chunks)}\n"
        f"[cyan]Elasticsearch:[/cyan] {elastic_host}:{elastic_port}",
        title="🎉 Elasticsearch Index"
    ))
