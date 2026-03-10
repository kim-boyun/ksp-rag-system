"""
Configuration management using pydantic-settings
Supports local/server mode switching via environment variables
"""
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """
    Application configuration
    Loads from .env (copy from .env.local or .env.server before run)
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # ================================
    # 실행 모드
    # ================================
    mode: Literal["local", "server"] = Field(
        default="local",
        description="Execution mode: local (development) or server (production)"
    )
    
    retriever_mode: Literal["local", "elastic"] = Field(
        default="local",
        description="Retriever mode: local (BM25+FAISS) or elastic (Elasticsearch)"
    )
    
    # ================================
    # 로컬 모드 설정
    # ================================
    local_embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="Local embedding model for BM25+FAISS"
    )
    
    # LLM Provider
    llm_provider: Literal["local_api", "server_http"] = Field(
        default="local_api",
        description="LLM provider: local_api (OpenAI) or server_http (vLLM)"
    )
    
    # LLM API (로컬 개발용)
    llm_api_type: str = Field(default="openai", description="LLM API type")
    llm_api_key: str = Field(default="", description="LLM API key")
    llm_model: str = Field(default="gpt-3.5-turbo", description="LLM model name")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2048, gt=0, description="Max tokens for answer (increase if answers get cut off)")
    
    # ================================
    # 서버 모드 설정
    # ================================
    # Elasticsearch
    elastic_host: str = Field(default="elasticsearch", description="Elasticsearch host")
    elastic_port: int = Field(default=9200, gt=0, lt=65536)
    elastic_index_name: str = Field(default="ksp_rag_index_m3", description="Elasticsearch index name (BGE-M3)")
    elastic_bm25_boost: float = Field(default=1.0, ge=0.0, description="BM25 clause boost (튜닝용)")
    elastic_dense_boost: float = Field(default=1.0, ge=0.0, description="Dense vector clause boost (튜닝용)")
    retrieval_min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="검색 결과 최소 점수(0=비활성). 결과를 max로 정규화한 뒤 이 값 미만 문서 제외")
    retrieval_skip_llm_if_max_below: float = Field(default=0.0, ge=0.0, description="검색 상위 문서 최고 점수가 이 값 미만이면 LLM 호출 없이 고정 메시지 반환(0=비활성). RRF 사용 시 약 0.02~0.05 구간 권장")
    
    # 서버 LLM (외부 vLLM HTTP endpoint)
    server_llm_base_url: str = Field(
        default="http://172.16.0.52:8000",
        description="External vLLM base URL (GPU server, without /v1/completions)"
    )
    server_llm_model: str = Field(
        default="meta-llama/Llama-2-7b-chat-hf",
        description="Server LLM model"
    )
    
    # 하위 호환성: SERVER_LLM_ENDPOINT가 있으면 사용 (deprecated)
    server_llm_endpoint: str | None = Field(
        default=None,
        description="[Deprecated] Full endpoint URL. Use SERVER_LLM_BASE_URL instead."
    )
    
    # ================================
    # 공통 설정
    # ================================
    chunk_size: int = Field(default=512, gt=0, description="Text chunk size")
    chunk_overlap: int = Field(default=80, ge=0, description="Chunk overlap (문장 경계 보존용 권장 80~100)")
    
    top_k: int = Field(default=5, gt=0, description="Number of documents to retrieve")
    rerank_top_k: int = Field(default=3, gt=0, description="Number of documents after reranking")

    # Cache (query -> response)
    cache_enabled: bool = Field(default=True, description="Enable response cache for repeated queries")
    cache_ttl_seconds: int = Field(default=3600, ge=0, description="Cache TTL in seconds (0 = no expiry)")
    cache_max_size: int = Field(default=1000, gt=0, description="Max cache entries (LRU eviction)")

    # Query expansion (multiple phrasings -> merge with RRF)
    query_expansion_enabled: bool = Field(default=True, description="Expand query to multiple phrasings before retrieval")
    query_expansion_num_queries: int = Field(default=3, ge=1, le=5, description="Number of query variants (including original)")

    log_level: str = Field(default="INFO", description="Logging level")

    # Ingest: figure/chart extraction (default False = text+table only, faster)
    extract_figures: bool = Field(default=False, description="Extract figures/charts during ingest (set true for --figures behavior)")

    @property
    def is_local_mode(self) -> bool:
        """Check if running in local mode"""
        return self.mode == "local"
    
    @property
    def is_server_mode(self) -> bool:
        """Check if running in server mode"""
        return self.mode == "server"
    
    def get_llm_endpoint(self) -> str:
        """Get LLM endpoint based on mode"""
        if self.is_local_mode:
            return f"openai:{self.llm_model}"
        # 하위 호환성: server_llm_endpoint가 있으면 사용
        if self.server_llm_endpoint:
            return self.server_llm_endpoint
        # 기본: BASE_URL + /v1/completions
        return f"{self.server_llm_base_url}/v1/completions"
    
    def get_llm_chat_endpoint(self) -> str:
        """Get LLM chat endpoint"""
        if self.is_local_mode:
            return f"openai:{self.llm_model}"
        # 하위 호환성: server_llm_endpoint가 있으면 변환
        if self.server_llm_endpoint:
            return self.server_llm_endpoint.replace("/completions", "/chat/completions")
        # 기본: BASE_URL + /v1/chat/completions
        return f"{self.server_llm_base_url}/v1/chat/completions"
    
    def get_retriever_type(self) -> str:
        """Get retriever type based on retriever_mode"""
        return "bm25+faiss" if self.retriever_mode == "local" else "elasticsearch"


# Global config instance
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """Reload configuration (useful for testing)"""
    global _config
    _config = AppConfig()
    return _config
