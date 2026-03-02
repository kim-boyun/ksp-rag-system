"""
Elasticsearch-based hybrid retriever
Supports BM25 + dense vector search with RRF
"""
import hashlib
from typing import List
from pathlib import Path
from loguru import logger
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan

# Elasticsearch _id must be <= 512 bytes; use hash when chunk_id is longer
MAX_ES_ID_BYTES = 512


def _doc_id(chunk_id: str) -> str:
    """Return ES-safe document id (<= 512 bytes). Uses SHA256 hex when chunk_id is too long."""
    raw = chunk_id.encode("utf-8")
    if len(raw) <= MAX_ES_ID_BYTES:
        return chunk_id
    return hashlib.sha256(raw).hexdigest()


def _doc_id_from_chunk_id(chunk_id: str) -> str:
    """Derive document name from chunk_id for display (e.g. KSP_Report_p12_c0 -> KSP_Report)."""
    if not chunk_id:
        return "Unknown"
    for sep in ("_p", "_table", "_figure"):
        if sep in chunk_id:
            return chunk_id.split(sep)[0]
    return chunk_id

from ragapp.pipeline.types import Document, Retriever
from ragapp.embeddings.bge import BGEEmbedding
from ragapp.config import get_config


class ElasticHybridRetriever(Retriever):
    """
    Elasticsearch-based hybrid retriever using BM25 + dense vectors
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        index_name: str = "ksp_rag_index",
        embedding_model: str = "BAAI/bge-m3"
    ):
        """
        Initialize Elasticsearch retriever
        
        Args:
            host: Elasticsearch host
            port: Elasticsearch port
            index_name: Index name
            embedding_model: Embedding model for dense vectors
        """
        self.host = host
        self.port = port
        self.index_name = index_name
        
        # Connect to Elasticsearch
        self.es = Elasticsearch(
            [f"http://{host}:{port}"],
            request_timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Check connection
        if not self.es.ping():
            raise ConnectionError(f"Cannot connect to Elasticsearch at {host}:{port}")
        
        logger.info(f"✅ Connected to Elasticsearch at {host}:{port}")
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedder = BGEEmbedding(model_name=embedding_model)
        
        logger.info(f"✅ ElasticHybridRetriever ready!")
        logger.info(f"Index: {index_name}")
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        doc_ids: List[str] | None = None,
        content_types: List[str] | None = None,
        **kwargs
    ) -> List[Document]:
        """
        Retrieve documents using Elasticsearch hybrid search.
        doc_ids, content_types 지정 시 메타데이터 필터 적용.
        """
        config = get_config()
        bm25_boost = config.elastic_bm25_boost
        dense_boost = config.elastic_dense_boost
        min_score_ratio = config.retrieval_min_score
        
        logger.info(f"🔍 Retrieving from Elasticsearch: {query}")
        logger.info(f"Top K: {top_k}")
        
        query_embedding = self.embedder.embed_query(query)
        
        must_clauses = []
        if doc_ids:
            must_clauses.append({"terms": {"metadata.doc_id": doc_ids}})
        if content_types:
            must_clauses.append({"terms": {"metadata.content_type": content_types}})
        
        bool_query = {
            "should": [
                {"match": {"content": {"query": query, "boost": bm25_boost}}},
                {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "(cosineSimilarity(params.query_vector, 'embedding') + 1.0) * params.dense_boost",
                            "params": {
                                "query_vector": query_embedding.tolist(),
                                "dense_boost": dense_boost,
                            },
                        },
                    }
                },
            ]
        }
        if must_clauses:
            bool_query["filter"] = must_clauses
        
        # min_score 적용을 위해 충분히 많이 가져온 뒤 후필터할 수 있음
        size = top_k * 2 if min_score_ratio > 0 else top_k
        
        search_body = {
            "size": size,
            "query": {"bool": bool_query},
            "_source": ["content", "metadata", "chunk_id"],
        }
        
        try:
            response = self.es.search(
                index=self.index_name,
                body=search_body
            )
            
            documents = []
            for hit in response['hits']['hits']:
                meta = dict(hit['_source'].get('metadata') or {})
                chunk_id = (hit['_source'] or {}).get('chunk_id') or ""
                if chunk_id:
                    meta['chunk_id'] = chunk_id
                if (not meta.get('doc_id') or meta.get('doc_id') == 'Unknown') and chunk_id:
                    meta['doc_id'] = _doc_id_from_chunk_id(chunk_id)
                if not meta.get('source_path') and meta.get('doc_id'):
                    meta['source_path'] = meta['doc_id']
                doc = Document(
                    content=hit['_source']['content'],
                    metadata=meta,
                    score=hit['_score']
                )
                documents.append(doc)
            
            # 관련도 임계값: 점수를 max로 정규화한 뒤 min_score_ratio 미만 제외
            if documents and min_score_ratio > 0:
                max_s = max(d.score for d in documents)
                if max_s > 0:
                    documents = [d for d in documents if (d.score / max_s) >= min_score_ratio]
                documents = documents[:top_k]
            else:
                documents = documents[:top_k]
            
            if len(documents) == 0:
                logger.warning(
                    "Elasticsearch returned 0 documents. "
                    "Check that the index has data (run: make index-elastic)"
                )
            else:
                logger.info(f"✅ Retrieved {len(documents)} documents from Elasticsearch")
            return documents
            
        except Exception as e:
            logger.error(f"Elasticsearch search failed: {e}")
            raise
    
    def index_exists(self) -> bool:
        """Check if index exists"""
        return self.es.indices.exists(index=self.index_name)

    def get_indexed_chunk_ids(self) -> set:
        """
        Return set of chunk_id already in the index (for resume).
        Reads chunk_id from _source so resume works even when _id is a hash.
        """
        if not self.index_exists():
            return set()
        try:
            hits = scan(
                self.es,
                index=self.index_name,
                query={"query": {"match_all": {}}},
                _source=["chunk_id"],
                size=10000,
            )
            out = set()
            for hit in hits:
                sid = (hit.get("_source") or {}).get("chunk_id")
                if sid is not None:
                    out.add(sid)
            return out
        except Exception as e:
            logger.warning(f"Could not list indexed IDs: {e}")
            return set()
    
    def create_index(self, embedding_dim: int = 384):
        """
        Create Elasticsearch index with hybrid search mapping
        
        Args:
            embedding_dim: Dimension of embedding vectors
        """
        if self.index_exists():
            logger.warning(f"Index {self.index_name} already exists")
            return
        
        mapping = {
            "mappings": {
                "properties": {
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": embedding_dim,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    },
                    "chunk_id": {
                        "type": "keyword"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "default": {
                            "type": "standard"
                        }
                    }
                }
            }
        }
        
        self.es.indices.create(index=self.index_name, body=mapping)
        logger.info(f"✅ Created index: {self.index_name}")
    
    def delete_index(self):
        """Delete index"""
        if self.index_exists():
            self.es.indices.delete(index=self.index_name)
            logger.info(f"🗑️  Deleted index: {self.index_name}")
    
    def bulk_index(self, chunks: List[dict], embeddings: List):
        """
        Bulk index chunks with embeddings
        
        Args:
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")
        
        # Prepare bulk actions (_id must be <= 512 bytes; use hash if chunk_id is longer)
        # metadata에 doc_id, source_path 포함 → UI에서 원본 파일명 표시용
        actions = []
        for chunk, embedding in zip(chunks, embeddings):
            cid = chunk.get("chunk_id") or ""
            meta = dict(chunk.get("metadata") or {})
            meta["doc_id"] = chunk.get("doc_id", "Unknown")
            meta["source_path"] = chunk.get("source_path", "")
            if "page_num" not in meta:
                meta["page_num"] = chunk.get("page_start")
            action = {
                "_index": self.index_name,
                "_id": _doc_id(cid),
                "_source": {
                    "content": chunk.get("content", ""),
                    "embedding": embedding.tolist(),
                    "metadata": meta,
                    "chunk_id": cid,
                }
            }
            actions.append(action)
        
        # Bulk index
        success, failed = bulk(self.es, actions, raise_on_error=False)
        
        logger.info(f"✅ Indexed {success} documents")
        if failed:
            logger.warning(f"⚠️  Failed to index {len(failed)} documents")
        
        # Refresh index
        self.es.indices.refresh(index=self.index_name)
