"""
Query expansion: generate multiple phrasings of a query and merge retrieval results with RRF.
"""
import re
from typing import List
from loguru import logger

from ragapp.pipeline.types import Document


def _looks_like_instruction(line: str) -> bool:
    """LLM이 지시문/메타 문장을 질문으로 출력한 경우 True. 검색 쿼리로 쓰이지 않도록 필터."""
    lower = line.lower().strip()
    if len(lower) < 10:
        return True
    # 지시/메타 패턴 (영어)
    meta_patterns = (
        "we need to", "we must", "let's ", "provide exactly", "output two",
        "alternative question", "same meaning", "rephrase", "each line",
        "original:", "the first answer", "two lines", "no numbering",
    )
    if any(p in lower for p in meta_patterns):
        return True
    # 번호만 있는 줄 (1. 2. 등으로 시작해 뒤에 짧은 문장)
    if re.match(r"^\d+[.)]\s*.{0,30}$", line):
        return True
    return False


def expand_query_with_llm(query: str, llm, num_extra: int = 2) -> List[str]:
    """
    Use LLM to generate num_extra alternative phrasings. Returns [original, p1, p2, ...].
    Instruction/meta lines from the model are filtered out so they are not sent as search queries.
    """
    if num_extra <= 0:
        return [query]
    prompt = f"""아래 질문과 **같은 의미**를 유지한 채, 단어나 표현만 바꾼 대체 질문을 정확히 {num_extra}개 만들어 주세요. 질문의 주제나 의도를 바꾸지 마세요.
각 줄에 질문 하나씩만 출력하고, 번호나 기호는 붙이지 마세요. 질문과 **같은 언어**로만 작성하세요.

질문: {query}"""
    try:
        out = llm.generate(prompt, max_tokens=150)
        lines = [s.strip() for s in (out or "").strip().split("\n") if s.strip()]
        seen = {query.strip().lower()}
        alternatives = [query]
        for line in lines:
            if len(alternatives) > num_extra:
                break
            if _looks_like_instruction(line):
                continue
            if line.lower() not in seen:
                seen.add(line.lower())
                alternatives.append(line)
        return alternatives[: num_extra + 1]
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}, using original only")
        return [query]


def merge_retrieval_results_rrf(
    list_of_docs: List[List[Document]],
    top_k: int = 20,
    k: int = 60,
) -> List[Document]:
    """
    Merge multiple retrieval runs with Reciprocal Rank Fusion (RRF).
    Each document is identified by (content, metadata.get("chunk_id")) to dedupe.
    """
    rrf_scores: dict[tuple, float] = {}
    doc_by_key: dict[tuple, Document] = {}

    for run in list_of_docs:
        for rank, doc in enumerate(run, start=1):
            key = (doc.content[:200], doc.metadata.get("chunk_id", ""))
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in doc_by_key:
                doc_by_key[key] = doc

    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])
    merged = []
    for key in sorted_keys[:top_k]:
        d = doc_by_key[key]
        # Update score to RRF score for consistency
        merged.append(Document(
            content=d.content,
            metadata=d.metadata,
            score=rrf_scores[key],
        ))
    return merged
