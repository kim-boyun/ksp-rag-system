"""
Prompt templates for RAG system
"""
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


def extract_citations(answer: str, documents: list) -> list:
    """
    Extract citations from answer
    
    Args:
        answer: Generated answer
        documents: Source documents
        
    Returns:
        List of citation dictionaries
    """
    import re
    
    citations = []
    
    # Find [출처: 문서 X] patterns
    pattern = r'\[출처:.*?문서\s*(\d+).*?\]'
    matches = re.findall(pattern, answer)
    
    for doc_num_str in matches:
        doc_num = int(doc_num_str)
        if 1 <= doc_num <= len(documents):
            doc = documents[doc_num - 1]
            citations.append({
                "doc_num": doc_num,
                "doc_id": doc.metadata.get('doc_id', 'Unknown'),
                "page_num": doc.metadata.get('page_num', 'N/A'),
                "chunk_id": doc.metadata.get('chunk_id', 'N/A'),
                "content_type": doc.metadata.get('content_type', 'text')
            })
    
    return citations
