"""
Build Elasticsearch index from chunks.
Streams the chunks file so that the full corpus is never loaded into memory (OOM-safe for 1M+ chunks).
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from rich.console import Console
from rich.panel import Panel

from ragapp.embeddings.bge import BGEEmbedding
from ragapp.retrievers.elastic_retriever import ElasticHybridRetriever


console = Console()

# 한 번에 읽어서 임베딩 후 ES에 넣는 단위. 메모리에 이 개수만 유지.
DEFAULT_INDEX_BATCH_SIZE = 10_000
# BGE-M3 등 대형 모델은 메모리 절약을 위해 작은 배치 권장
INDEX_BATCH_SIZE_M3 = 3_000
# 이 길이 미만 content는 인덱싱 스킵 (노이즈 감소)
MIN_CONTENT_LENGTH_FOR_INDEX = 10


def build_elastic_index(
    chunks_file: str,
    elastic_host: str = "localhost",
    elastic_port: int = 9200,
    index_name: str = "ksp_rag_index",
    embedding_model: str = "BAAI/bge-m3",
    batch_size: int = 32,
    index_batch_size: int = None,
    recreate: bool = False
):
    """
    Build Elasticsearch index from chunks (streaming: does not load full file into memory).

    Args:
        chunks_file: Path to chunks JSONL file
        elastic_host: Elasticsearch host
        elastic_port: Elasticsearch port
        index_name: Index name
        embedding_model: Embedding model
        batch_size: Batch size for embedding
        index_batch_size: Chunks per streaming batch (default: smaller for bge-m3 to reduce memory)
        recreate: Whether to recreate index if exists
    """
    if index_batch_size is None:
        index_batch_size = INDEX_BATCH_SIZE_M3 if "bge-m3" in embedding_model.lower() else DEFAULT_INDEX_BATCH_SIZE
    logger.info("=" * 60)
    logger.info("Building Elasticsearch Hybrid Index (streaming)")
    logger.info("=" * 60)
    logger.info(f"Input: {chunks_file}")
    logger.info(f"Elasticsearch: {elastic_host}:{elastic_port}")
    logger.info(f"Index: {index_name}")
    logger.info(f"Embedding model: {embedding_model}")

    chunks_path = Path(chunks_file)
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")

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

    # Resume: chunks already in the index (when not recreating)
    indexed_ids: set = set()
    if not recreate:
        logger.info("\n📋 Checking already indexed chunks (resume)...")
        indexed_ids = retriever.get_indexed_chunk_ids()
        if indexed_ids:
            logger.info(f"Found {len(indexed_ids)} chunks already in index; will skip and index only the rest.")

    # Stream file: read batch -> filter by indexed_ids -> embed -> bulk_index -> discard
    logger.info("\n🤖 Streaming chunks (batch size=%s, progress saved each batch)...", index_batch_size)
    indexed_this_run = 0
    batch: List[Dict[str, Any]] = []

    with open(chunks_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("Skipping invalid JSON line: %s", e)
                continue
            cid = chunk.get("chunk_id")
            if cid is not None and cid in indexed_ids:
                continue
            batch.append(chunk)
            if len(batch) >= index_batch_size:
                valid = [c for c in batch if len((c.get("content") or "").strip()) >= MIN_CONTENT_LENGTH_FOR_INDEX]
                if valid:
                    batch_texts = [c.get("content", "") for c in valid]
                    embeddings = retriever.embedder.embed_documents(batch_texts, batch_size=batch_size)
                    retriever.bulk_index(valid, embeddings)
                    for c in valid:
                        if c.get("chunk_id") is not None:
                            indexed_ids.add(c["chunk_id"])
                    indexed_this_run += len(valid)
                if len(valid) < len(batch):
                    logger.debug("Skipped %s short chunks in batch", len(batch) - len(valid))
                logger.info("Indexed %s chunks so far (batch done)", indexed_this_run)
                batch = []

        if batch:
            valid = [c for c in batch if len((c.get("content") or "").strip()) >= MIN_CONTENT_LENGTH_FOR_INDEX]
            if valid:
                batch_texts = [c.get("content", "") for c in valid]
                embeddings = retriever.embedder.embed_documents(batch_texts, batch_size=batch_size)
                retriever.bulk_index(valid, embeddings)
                for c in valid:
                    if c.get("chunk_id") is not None:
                        indexed_ids.add(c["chunk_id"])
                indexed_this_run += len(valid)
            if len(valid) < len(batch):
                logger.debug("Skipped %s short chunks in final batch", len(batch) - len(valid))
            logger.info("Indexed %s chunks (final batch)", indexed_this_run)

    total_in_index = len(indexed_ids)
    logger.info("\n🎉 Elasticsearch index built successfully!")
    logger.info(f"Index: {index_name}")
    logger.info(f"Indexed this run: {indexed_this_run} | Total in index: {total_in_index}")

    console.print(Panel.fit(
        f"[bold green]✅ Index built successfully![/bold green]\n\n"
        f"[cyan]Index:[/cyan] {index_name}\n"
        f"[cyan]Indexed this run:[/cyan] {indexed_this_run}\n"
        f"[cyan]Total in index:[/cyan] {total_in_index}\n"
        f"[cyan]Elasticsearch:[/cyan] {elastic_host}:{elastic_port}",
        title="🎉 Elasticsearch Index"
    ))
