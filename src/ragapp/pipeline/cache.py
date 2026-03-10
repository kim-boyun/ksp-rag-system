"""
In-memory cache for RAG responses.
Reduces latency and cost for repeated or similar queries.
"""
import hashlib
import time
from typing import Any, Optional
from collections import OrderedDict
from loguru import logger

from ragapp.pipeline.types import RAGResponse, Document


def _cache_key(
    query: str,
    mode: str,
    top_k: int,
    *,
    use_rerank: bool = False,
    retrieval_params: str = "",
) -> str:
    """캐시 키: 질문·모드·top_k·리랭크·검색 파라미터 해시. UI에서 설정 변경 시 스태일 캐시 방지."""
    raw = f"{query.strip().lower()}|{mode}|{top_k}|{use_rerank}|{retrieval_params}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _response_to_dict(res: RAGResponse) -> dict:
    return {
        "answer": res.answer,
        "retrieved_docs": [
            {"content": d.content, "metadata": d.metadata, "score": d.score}
            for d in res.retrieved_docs
        ],
        "metadata": {**res.metadata, "_cached": True},
    }


def _dict_to_response(data: dict) -> RAGResponse:
    docs = [
        Document(content=d["content"], metadata=d["metadata"], score=d["score"])
        for d in data["retrieved_docs"]
    ]
    return RAGResponse(
        answer=data["answer"],
        retrieved_docs=docs,
        metadata=data["metadata"],
    )


class ResponseCache:
    """
    LRU in-memory cache with optional TTL.
    Thread-safe for single-process use.
    """
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, tuple[float, dict]] = OrderedDict()

    def get(self, key: str) -> Optional[dict]:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        ts, data = self._store[key]
        if self.ttl_seconds > 0 and (time.time() - ts) > self.ttl_seconds:
            del self._store[key]
            return None
        return data

    def set(self, key: str, data: dict) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        else:
            if len(self._store) >= self.max_size:
                self._store.popitem(last=False)
        self._store[key] = (time.time(), data)

    def clear(self) -> None:
        self._store.clear()
        logger.info("Response cache cleared")


_global_cache: Optional[ResponseCache] = None


def get_cache(max_size: int = 1000, ttl_seconds: int = 3600) -> ResponseCache:
    global _global_cache
    if _global_cache is None:
        _global_cache = ResponseCache(max_size=max_size, ttl_seconds=ttl_seconds)
    return _global_cache


def get_cached_response(
    query: str,
    mode: str,
    top_k: int,
    cache: ResponseCache,
    *,
    use_rerank: bool = False,
    retrieval_params: str = "",
) -> Optional[RAGResponse]:
    if not query or not query.strip():
        return None
    key = _cache_key(query, mode, top_k, use_rerank=use_rerank, retrieval_params=retrieval_params)
    data = cache.get(key)
    if data is None:
        return None
    logger.info("Cache hit for query")
    return _dict_to_response(data)


def set_cached_response(
    query: str,
    mode: str,
    top_k: int,
    response: RAGResponse,
    cache: ResponseCache,
    *,
    use_rerank: bool = False,
    retrieval_params: str = "",
) -> None:
    if not query or not query.strip():
        return
    key = _cache_key(query, mode, top_k, use_rerank=use_rerank, retrieval_params=retrieval_params)
    cache.set(key, _response_to_dict(response))
    logger.debug("Cached response for query")
