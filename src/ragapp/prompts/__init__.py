"""
Prompt templates for RAG system
"""
import re
from pathlib import Path


def load_prompt(prompt_name: str) -> str:
    """
    Load prompt template from file
    
    Args:
        prompt_name: Name of prompt file (without .txt extension)
        
    Returns:
        Prompt template string
    """
    prompt_dir = Path(__file__).parent
    prompt_file = prompt_dir / f"{prompt_name}.txt"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_file}")
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def format_qa_prompt(question: str, documents: list) -> str:
    """
    Format QA prompt with question and documents
    
    Args:
        question: User question
        documents: List of Document objects
        
    Returns:
        Formatted prompt
    """
    qa_template = load_prompt("qa")
    
    # Format documents with clear numbering
    context_parts = []
    for i, doc in enumerate(documents, 1):
        doc_id = doc.metadata.get('doc_id', 'Unknown')
        page = doc.metadata.get('page_num', 'N/A')
        chunk_id = doc.metadata.get('chunk_id', 'N/A')
        content_type = doc.metadata.get('content_type', 'text')
        
        context_parts.append(
            f"[문서 {i}]\n"
            f"출처: {doc_id}\n"
            f"페이지: {page}\n"
            f"청크 ID: {chunk_id}\n"
            f"유형: {content_type}\n"
            f"내용:\n{doc.content}\n"
        )
    
    context = "\n---\n\n".join(context_parts)
    
    # Fill template
    prompt = qa_template.replace("{context}", context)
    prompt = prompt.replace("{question}", question)
    
    return prompt


def clean_rag_answer(raw: str) -> str:
    """
    Remove reasoning/meta-commentary from model output so only the final answer is shown.
    """
    if not raw or not raw.strip():
        return raw
    text = raw.strip()
    # Take content after common "final answer" markers (model sometimes appends answer here)
    for marker in [
        "assistantfinal",
        "Thus final answer.",
        "Thus final answer",
        "final answer.",
        "final answer:",
        "Final answer:",
        "Final answer.",
    ]:
        if marker.lower() in text.lower():
            idx = text.lower().rfind(marker.lower())
            after = text[idx + len(marker) :].strip()
            if len(after) > 10 and ("출처" in after or "문서" in after or any("\uac00" <= c <= "\ud7a3" for c in after)):
                text = after
                break
    # Drop lines that are clearly reasoning (English meta-commentary)
    reasoning_starts = (
        "We need to answer",
        "We need to follow",
        "We must use",
        "We must ",
        "Let's examine",
        "Thus none",
        "Thus answer",
        "So we can say",
        "Could just cite",
        "Document 1:",
        "Document 2:",
        "Document 3:",
        "Document 4:",
        "Document 5:",
        "Not helpful.",
        "Not about ",
    )
    lines = text.split("\n")
    kept = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(s) or s in stripped for s in reasoning_starts):
            continue
        # Skip line that is only backtick-quoted meta
        if stripped.startswith("`") and stripped.endswith("`") and "document" in stripped.lower() and "출처" not in stripped:
            continue
        kept.append(line)
    result = "\n".join(kept).strip()
    # Normalize multiple newlines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result if result else raw.strip()


def extract_citations(answer: str, documents: list) -> list:
    """
    Extract citations from answer. Handles both [출처: 문서 1] and [출처: 문서 1, 문서 2, 문서 3].
    """
    citations = []
    seen = set()
    # Find all [출처: ...] blocks
    blocks = re.findall(r'\[출처:[^\]]*\]', answer)
    for block in blocks:
        # Extract all document numbers in this block (문서 1, 문서 2, ...)
        for doc_num_str in re.findall(r'문서\s*(\d+)', block):
            doc_num = int(doc_num_str)
            if doc_num in seen or doc_num < 1 or doc_num > len(documents):
                continue
            seen.add(doc_num)
            doc = documents[doc_num - 1]
            citations.append({
                "doc_num": doc_num,
                "doc_id": doc.metadata.get('doc_id', 'Unknown'),
                "page_num": doc.metadata.get('page_num', 'N/A'),
                "chunk_id": doc.metadata.get('chunk_id', 'N/A'),
                "content_type": doc.metadata.get('content_type', 'text')
            })
    return citations
