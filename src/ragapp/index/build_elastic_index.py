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

# 한 번에 임베딩 후 ES에 넣는 단위. 이만큼 넣을 때마다 저장되므로 중간에 꺼져도 resume 가능.
INDEX_BATCH_SIZE = 10_000


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

    # Resume: skip chunks already in the index (when not recreating)
    indexed_ids = set()
    if not recreate:
        logger.info("\n📋 Checking already indexed chunks (resume)...")
        indexed_ids = retriever.get_indexed_chunk_ids()
        if indexed_ids:
            logger.info(f"Found {len(indexed_ids)} chunks already in index; will skip and index only the rest.")
    chunks_to_index = [c for c in chunks if c.get("chunk_id") not in indexed_ids]
    skipped = len(chunks) - len(chunks_to_index)
    if skipped:
        logger.info(f"Skipping {skipped} already indexed; {len(chunks_to_index)} chunks to index.")
    if not chunks_to_index:
        logger.info("Nothing to index (all chunks already present). Done.")
        console.print(Panel.fit(
            f"[bold green]✅ Index already up to date![/bold green]\n\n"
            f"[cyan]Index:[/cyan] {index_name}\n"
            f"[cyan]Total chunks in index:[/cyan] {len(indexed_ids)}",
            title="🎉 Elasticsearch Index"
        ))
        return

    # 일정 개수마다 임베딩 → ES 저장 반복. 중간에 꺼져도 그때까지 저장분은 유지되고 다음에 resume 됨.
    total_to_index = len(chunks_to_index)
    indexed_this_run = 0
    logger.info("\n🤖 Embedding + indexing in batches of %s (progress saved each batch)...", INDEX_BATCH_SIZE)

    for start in range(0, total_to_index, INDEX_BATCH_SIZE):
        end = min(start + INDEX_BATCH_SIZE, total_to_index)
        batch = chunks_to_index[start:end]
        batch_texts = [chunk.get("content", "") for chunk in batch]
        embeddings = retriever.embedder.embed_documents(batch_texts, batch_size=batch_size)
        retriever.bulk_index(batch, embeddings)
        indexed_this_run += len(batch)
        logger.info("Indexed %s / %s (%.1f%%)", indexed_this_run, total_to_index, 100.0 * indexed_this_run / total_to_index)

    total_in_index = len(indexed_ids) + indexed_this_run
    logger.info("\n🎉 Elasticsearch index built successfully!")
    logger.info(f"Index: {index_name}")
    logger.info(f"Indexed this run: {indexed_this_run} | Total in index: {total_in_index}")

    # Print summary
    console.print(Panel.fit(
        f"[bold green]✅ Index built successfully![/bold green]\n\n"
        f"[cyan]Index:[/cyan] {index_name}\n"
        f"[cyan]Indexed this run:[/cyan] {indexed_this_run}\n"
        f"[cyan]Total in index:[/cyan] {total_in_index}\n"
        f"[cyan]Elasticsearch:[/cyan] {elastic_host}:{elastic_port}",
        title="🎉 Elasticsearch Index"
    ))
