"""
Query expansion: generate multiple phrasings of a query and merge retrieval results with RRF.
"""
from typing import List
from loguru import logger

from ragapp.pipeline.types import Document


def expand_query_with_llm(query: str, llm, num_extra: int = 2) -> List[str]:
    """
    Use LLM to generate num_extra alternative phrasings. Returns [original, p1, p2, ...].
    """
    if num_extra <= 0:
        return [query]
    prompt = f"""Generate exactly {num_extra} different phrasings of the following question. Each line must be one alternative question. Same meaning, different words. Output only the {num_extra} questions, one per line, no numbering.

Question: {query}"""
    try:
        out = llm.generate(prompt, max_tokens=150)
        lines = [s.strip() for s in (out or "").strip().split("\n") if s.strip()]
        # Take first num_extra; avoid duplicates
        seen = {query.strip().lower()}
        alternatives = [query]
        for line in lines:
            if line.lower() not in seen and len(alternatives) <= num_extra:
                seen.add(line.lower())
                alternatives.append(line)
            if len(alternatives) > num_extra:
                break
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
