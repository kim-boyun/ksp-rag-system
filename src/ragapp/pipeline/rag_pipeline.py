"""
RAG Pipeline orchestration
"""
from typing import List, Generator, Dict, Any, Tuple
from pathlib import Path
from loguru import logger

from ragapp.config import get_config
from ragapp.pipeline.types import Document, RAGResponse, Retriever, Reranker, LLMClient
from ragapp.pipeline.cache import (
    get_cache,
    get_cached_response,
    set_cached_response,
)
from ragapp.pipeline.query_expansion import (
    expand_query_with_llm,
    merge_retrieval_results_rrf,
)


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
        Process a query through the RAG pipeline.
        Uses cache and optional query expansion when enabled in config.
        """
        logger.info(f"Processing query: {query}")
        if use_rerank is None:
            use_rerank = self.use_rerank
        mode = self.config.mode
        top_k = self.config.top_k

        # Cache lookup (설정 변경 시 스태일 캐시 방지를 위해 use_rerank·검색 파라미터 포함)
        retrieval_params = (
            f"{self.config.elastic_bm25_boost}|{self.config.elastic_dense_boost}"
            f"|{self.config.retrieval_min_score}|{self.config.retrieval_skip_llm_if_max_below}"
            f"|{self.config.query_expansion_enabled}"
        )
        if self.config.cache_enabled:
            cache = get_cache(
                max_size=self.config.cache_max_size,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            cached = get_cached_response(
                query, mode, top_k, cache,
                use_rerank=use_rerank,
                retrieval_params=retrieval_params,
            )
            if cached is not None:
                return cached

        # Step 1: Query expansion (optional) + Retrieve
        if self.config.query_expansion_enabled and self.config.query_expansion_num_queries > 1:
            num_extra = self.config.query_expansion_num_queries - 1
            queries = expand_query_with_llm(query, self.llm, num_extra=num_extra)
            logger.info(f"Query expansion: {len(queries)} variants")
            list_of_docs = []
            for q in queries:
                docs = self.retriever.retrieve(q, top_k=top_k * 2)
                list_of_docs.append(docs)
            retrieved_docs = merge_retrieval_results_rrf(
                list_of_docs,
                top_k=top_k,
                k=60,
            )
            logger.info(f"Retrieved {len(retrieved_docs)} documents (after RRF merge)")
        else:
            retrieved_docs = self.retriever.retrieve(query, top_k=top_k)
            logger.info(f"Retrieved {len(retrieved_docs)} documents")

        # Step 2: Rerank (if enabled)
        if use_rerank:
            reranked_docs = self.reranker.rerank(
                query,
                retrieved_docs,
                top_k=self.config.rerank_top_k,
            )
            logger.info(f"Reranked to {len(reranked_docs)} documents")
        else:
            reranked_docs = retrieved_docs

        # Step 2.5: 검색 결과 없거나, 최고 점수가 임계값 미만이면 LLM 호출 없이 고정 메시지 반환
        no_docs_message = (
            "제공된 문서에서 관련 정보를 찾을 수 없습니다. "
            "질문을 바꾸거나 담당자에게 문의해 주세요."
        )
        if not reranked_docs:
            return RAGResponse(
                answer=no_docs_message,
                retrieved_docs=[],
                metadata={
                    "mode": mode,
                    "retriever": self.config.get_retriever_type(),
                    "llm_provider": self.config.llm_provider,
                    "rerank_enabled": use_rerank,
                    "num_docs": 0,
                    "skipped_llm": True,
                },
            )
        skip_threshold = self.config.retrieval_skip_llm_if_max_below
        if skip_threshold > 0:
            best_score = max(d.score for d in reranked_docs)
            if best_score < skip_threshold:
                logger.info(f"Skipping LLM: best retrieval score {best_score:.4f} < {skip_threshold}")
                return RAGResponse(
                    answer=no_docs_message,
                    retrieved_docs=reranked_docs,
                    metadata={
                        "mode": mode,
                        "retriever": self.config.get_retriever_type(),
                        "llm_provider": self.config.llm_provider,
                        "rerank_enabled": use_rerank,
                        "num_docs": len(reranked_docs),
                        "skipped_llm": True,
                        "best_score_below_threshold": best_score,
                    },
                )

        # Step 3: Generate (system 프롬프트 적용)
        prompt = self._build_prompt(query, reranked_docs)
        system_prompt = self._load_system_prompt()
        answer = self.llm.generate(
            prompt,
            max_tokens=self.config.llm_max_tokens,
            system_prompt=system_prompt,
        )
        from ragapp.prompts import clean_rag_answer
        answer = clean_rag_answer(answer)
        logger.info("Generated answer")

        response = RAGResponse(
            answer=answer,
            retrieved_docs=reranked_docs,
            metadata={
                "mode": mode,
                "retriever": self.config.get_retriever_type(),
                "llm_provider": self.config.llm_provider,
                "rerank_enabled": use_rerank,
                "num_docs": len(reranked_docs),
            },
        )

        # Cache store
        if self.config.cache_enabled:
            cache = get_cache(
                max_size=self.config.cache_max_size,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
            set_cached_response(
                query, mode, top_k, response, cache,
                use_rerank=use_rerank,
                retrieval_params=retrieval_params,
            )

        return response

    def ask_stream(
        self, query: str, use_rerank: bool = None
    ) -> Tuple[Generator[str, None, None], Dict[str, Any]]:
        """
        Same as ask() but yields answer text chunk by chunk.
        Returns (chunk_generator, result_holder). After consuming the generator,
        result_holder["response"] will be the RAGResponse (with cleaned answer).
        Cache is skipped for streaming.
        """
        if use_rerank is None:
            use_rerank = self.use_rerank
        mode = self.config.mode
        top_k = self.config.top_k
        result_holder: Dict[str, Any] = {}

        # Step 1: Retrieve (no cache for stream)
        if self.config.query_expansion_enabled and self.config.query_expansion_num_queries > 1:
            num_extra = self.config.query_expansion_num_queries - 1
            queries = expand_query_with_llm(query, self.llm, num_extra=num_extra)
            list_of_docs = []
            for q in queries:
                docs = self.retriever.retrieve(q, top_k=top_k * 2)
                list_of_docs.append(docs)
            retrieved_docs = merge_retrieval_results_rrf(
                list_of_docs, top_k=top_k, k=60
            )
        else:
            retrieved_docs = self.retriever.retrieve(query, top_k=top_k)

        # Step 2: Rerank
        if use_rerank:
            reranked_docs = self.reranker.rerank(
                query, retrieved_docs, top_k=self.config.rerank_top_k
            )
        else:
            reranked_docs = retrieved_docs

        no_docs_message = (
            "제공된 문서에서 관련 정보를 찾을 수 없습니다. "
            "질문을 바꾸거나 담당자에게 문의해 주세요."
        )
        if not reranked_docs:
            def gen_empty():
                yield no_docs_message
            result_holder["response"] = RAGResponse(
                answer=no_docs_message,
                retrieved_docs=[],
                metadata={
                    "mode": mode,
                    "retriever": self.config.get_retriever_type(),
                    "llm_provider": self.config.llm_provider,
                    "rerank_enabled": use_rerank,
                    "num_docs": 0,
                    "skipped_llm": True,
                },
            )
            return gen_empty(), result_holder
        skip_threshold = self.config.retrieval_skip_llm_if_max_below
        if skip_threshold > 0:
            best_score = max(d.score for d in reranked_docs)
            if best_score < skip_threshold:
                def gen_skip():
                    yield no_docs_message
                result_holder["response"] = RAGResponse(
                    answer=no_docs_message,
                    retrieved_docs=reranked_docs,
                    metadata={
                        "mode": mode,
                        "retriever": self.config.get_retriever_type(),
                        "llm_provider": self.config.llm_provider,
                        "rerank_enabled": use_rerank,
                        "num_docs": len(reranked_docs),
                        "skipped_llm": True,
                        "best_score_below_threshold": best_score,
                    },
                )
                return gen_skip(), result_holder

        prompt = self._build_prompt(query, reranked_docs)
        system_prompt = self._load_system_prompt()
        from ragapp.prompts import clean_rag_answer

        def gen() -> Generator[str, None, None]:
            full: List[str] = []
            if hasattr(self.llm, "generate_stream"):
                for chunk in self.llm.generate_stream(
                    prompt,
                    max_tokens=self.config.llm_max_tokens,
                    system_prompt=system_prompt,
                ):
                    full.append(chunk)
                    yield chunk
            else:
                text = self.llm.generate(
                    prompt,
                    max_tokens=self.config.llm_max_tokens,
                    system_prompt=system_prompt,
                )
                full.append(text)
                yield text
            answer = clean_rag_answer("".join(full))
            result_holder["response"] = RAGResponse(
                answer=answer,
                retrieved_docs=reranked_docs,
                metadata={
                    "mode": mode,
                    "retriever": self.config.get_retriever_type(),
                    "llm_provider": self.config.llm_provider,
                    "rerank_enabled": use_rerank,
                    "num_docs": len(reranked_docs),
                },
            )

        return gen(), result_holder

    def _load_system_prompt(self) -> str:
        """Load system prompt from prompts/system.txt"""
        try:
            from ragapp.prompts import load_prompt
            return load_prompt("system")
        except FileNotFoundError:
            return ""

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
            def generate(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
                logger.warning("Using placeholder LLM")
                return f"[Placeholder answer] This is a mock response. In production, this would be generated by {get_config().llm_provider}."
        
        return PlaceholderLLM()
