"""
Elasticsearch-based hybrid retriever
Supports BM25 + dense vector search with RRF
"""
from typing import List
from pathlib import Path
from loguru import logger
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan

from ragapp.pipeline.types import Document, Retriever
from ragapp.embeddings.bge import BGEEmbedding


class ElasticHybridRetriever(Retriever):
    """
    Elasticsearch-based hybrid retriever using BM25 + dense vectors
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        index_name: str = "ksp_rag_index",
        embedding_model: str = "BAAI/bge-small-en-v1.5"
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
        **kwargs
    ) -> List[Document]:
        """
        Retrieve documents using Elasticsearch hybrid search
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of retrieved documents
        """
        logger.info(f"🔍 Retrieving from Elasticsearch: {query}")
        logger.info(f"Top K: {top_k}")
        
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        # Hybrid search with RRF (Reciprocal Rank Fusion)
        # Elasticsearch 8.12+ supports RRF natively
        search_body = {
            "size": top_k,
            "query": {
                "bool": {
                    "should": [
                        # BM25 search on text field
                        {
                            "match": {
                                "content": {
                                    "query": query,
                                    "boost": 1.0
                                }
                            }
                        },
                        # Dense vector search
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {
                                        "query_vector": query_embedding.tolist()
                                    }
                                }
                            }
                        }
                    ]
                }
            },
            "_source": ["content", "metadata", "chunk_id"]
        }
        
        try:
            response = self.es.search(
                index=self.index_name,
                body=search_body
            )
            
            # Convert to Document objects
            documents = []
            for hit in response['hits']['hits']:
                doc = Document(
                    content=hit['_source']['content'],
                    metadata=hit['_source'].get('metadata', {}),
                    score=hit['_score']
                )
                documents.append(doc)
            
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
        Uses scan with _source=False to only fetch _id.
        """
        if not self.index_exists():
            return set()
        try:
            hits = scan(
                self.es,
                index=self.index_name,
                query={"query": {"match_all": {}}},
                _source=False,
                size=10000,
            )
            return {hit["_id"] for hit in hits}
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
        
        # Prepare bulk actions
        actions = []
        for chunk, embedding in zip(chunks, embeddings):
            action = {
                "_index": self.index_name,
                "_id": chunk.get("chunk_id"),
                "_source": {
                    "content": chunk.get("content", ""),
                    "embedding": embedding.tolist(),
                    "metadata": chunk.get("metadata", {}),
                    "chunk_id": chunk.get("chunk_id", "")
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
