"""
RAG Pipeline orchestration
"""
from typing import List
from pathlib import Path
from loguru import logger

from ragapp.config import get_config
from ragapp.pipeline.types import Document, RAGResponse, Retriever, Reranker, LLMClient


class RAGPipeline:
    """
    Main RAG pipeline orchestrator
    Coordinates retrieval, reranking, and generation
    """
    
    def __init__(
        self,
        retriever: Retriever | None = None,
        reranker: Reranker | None = None,
        llm: LLMClient | None = None,
        use_rerank: bool = False
    ):
        self.config = get_config()
        self.use_rerank = use_rerank
        
        # Initialize components
        if retriever is None:
            self.retriever = self._create_retriever()
        else:
            self.retriever = retriever
        
        if reranker is None:
            self.reranker = self._create_reranker()
        else:
            self.reranker = reranker
        
        if llm is None:
            self.llm = self._create_llm()
        else:
            self.llm = llm
        
        logger.info(f"RAG Pipeline initialized in {self.config.mode} mode")
        logger.info(f"Retriever type: {self.config.get_retriever_type()}")
        logger.info(f"LLM provider: {self.config.llm_provider}")
        logger.info(f"Rerank enabled: {self.use_rerank}")
    
    def ask(self, query: str, use_rerank: bool = None) -> RAGResponse:
        """
        Process a query through the RAG pipeline
        
        Args:
            query: User query
            use_rerank: Override rerank setting
            
        Returns:
            RAG response with answer and retrieved documents
        """
        logger.info(f"Processing query: {query}")
        
        if use_rerank is None:
            use_rerank = self.use_rerank
        
        # Step 1: Retrieve
        retrieved_docs = self.retriever.retrieve(query, top_k=self.config.top_k)
        logger.info(f"Retrieved {len(retrieved_docs)} documents")
        
        # Step 2: Rerank (if enabled)
        if use_rerank:
            reranked_docs = self.reranker.rerank(
                query,
                retrieved_docs,
                top_k=self.config.rerank_top_k
            )
            logger.info(f"Reranked to {len(reranked_docs)} documents")
        else:
            # No reranking: use all retrieved documents
            reranked_docs = retrieved_docs
            logger.info(f"Using all {len(reranked_docs)} retrieved documents (no rerank)")
        
        # Step 3: Generate
        prompt = self._build_prompt(query, reranked_docs)
        answer = self.llm.generate(prompt, max_tokens=self.config.llm_max_tokens)
        logger.info("Generated answer")
        
        return RAGResponse(
            answer=answer,
            retrieved_docs=reranked_docs,
            metadata={
                "mode": self.config.mode,
                "retriever": self.config.get_retriever_type(),
                "llm_provider": self.config.llm_provider,
                "rerank_enabled": use_rerank,
                "num_docs": len(reranked_docs)
            }
        )
    
    def _build_prompt(self, query: str, documents: List[Document]) -> str:
        """Build LLM prompt from query and documents"""
        from ragapp.prompts import format_qa_prompt
        return format_qa_prompt(query, documents)
    
    # ================================
    # Component factory methods
    # ================================
    
    def _create_retriever(self) -> Retriever:
        """Create retriever based on retriever_mode"""
        if self.config.retriever_mode == "elastic":
            # Use Elasticsearch hybrid retriever
            try:
                from ragapp.retrievers.elastic_retriever import ElasticHybridRetriever
                
                retriever = ElasticHybridRetriever(
                    host=self.config.elastic_host,
                    port=self.config.elastic_port,
                    index_name=self.config.elastic_index_name,
                    embedding_model=self.config.local_embedding_model
                )
                
                # Check if index exists
                if not retriever.index_exists():
                    logger.warning(f"Elasticsearch index '{self.config.elastic_index_name}' not found")
                    logger.warning("Run 'python -m ragapp index-elastic' first")
                    return self._create_placeholder_retriever()
                
                return retriever
            except Exception as e:
                logger.error(f"Failed to create Elasticsearch retriever: {e}")
                return self._create_placeholder_retriever()
        else:
            # Use local hybrid retriever (BM25 + FAISS)
            try:
                from ragapp.retrievers.local_hybrid import LocalHybridRetriever
                index_path = Path("data/index")
                
                if not index_path.exists() or not (index_path / "faiss.index").exists():
                    logger.warning("Local index not found, using placeholder")
                    return self._create_placeholder_retriever()
                
                return LocalHybridRetriever(index_path)
            except Exception as e:
                logger.warning(f"Failed to load local retriever: {e}")
                return self._create_placeholder_retriever()
    
    def _create_reranker(self) -> Reranker:
        """Create reranker based on config"""
        if self.use_rerank:
            try:
                from ragapp.rerankers.llm_reranker import LLMReranker
                return LLMReranker()
            except Exception as e:
                logger.warning(f"Failed to create LLM reranker: {e}")
                from ragapp.rerankers.base import NoOpReranker
                return NoOpReranker()
        else:
            from ragapp.rerankers.base import NoOpReranker
            return NoOpReranker()
    
    def _create_llm(self) -> LLMClient:
        """Create LLM client based on provider"""
        try:
            if self.config.llm_provider == "local_api":
                from ragapp.llms.local_api import LocalAPIClient
                return LocalAPIClient()
            elif self.config.llm_provider == "server_http":
                from ragapp.llms.server_http import ServerHTTPClient
                return ServerHTTPClient()
            else:
                raise ValueError(f"Unknown LLM provider: {self.config.llm_provider}")
        except Exception as e:
            logger.warning(f"Failed to create LLM client: {e}")
            return self._create_placeholder_llm()
    
    def _create_placeholder_retriever(self) -> Retriever:
        """Create placeholder retriever"""
        class PlaceholderRetriever:
            def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
                logger.warning("Using placeholder retriever")
                return [
                    Document(
                        content=f"Placeholder document {i+1} for query: {query}",
                        metadata={"source": "placeholder", "index": i},
                        score=1.0 / (i + 1)
                    )
                    for i in range(top_k)
                ]
        
        return PlaceholderRetriever()
    
    def _create_placeholder_llm(self) -> LLMClient:
        """Create placeholder LLM"""
        class PlaceholderLLM:
            def generate(self, prompt: str, max_tokens: int = 1000) -> str:
                logger.warning("Using placeholder LLM")
                return f"[Placeholder answer] This is a mock response. In production, this would be generated by {get_config().llm_provider}."
        
        return PlaceholderLLM()
