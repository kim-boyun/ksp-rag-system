"""
Text chunking with semantic splitting
Splits documents into smaller chunks for retrieval
"""
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import hashlib
from loguru import logger

from langchain_text_splitters import RecursiveCharacterTextSplitter
from ragapp.config import get_config
from ragapp.ingest.loaders import PDFDocument


@dataclass
class Chunk:
    """
    Text chunk with metadata
    """
    chunk_id: str
    doc_id: str
    source_path: str
    page_start: int
    page_end: int
    content: str
    content_type: str  # "text" | "table_md" | "table_html" | "figure"
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_jsonl(self) -> str:
        """Convert to JSONL line"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)


# 이 길이 미만의 청크는 스킵 (노이즈·불완전 문장 감소)
MIN_CHUNK_LENGTH = 15


class TextChunker:
    """
    Text chunker using LangChain's RecursiveCharacterTextSplitter
    Splits by paragraph, sentence, then character.
    Very short chunks (< MIN_CHUNK_LENGTH) are skipped.
    """
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        config = get_config()
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        logger.info(f"TextChunker initialized: size={self.chunk_size}, overlap={self.chunk_overlap}")
    
    def chunk_document(self, doc: PDFDocument) -> List[Chunk]:
        """
        Chunk a PDF document page-by-page
        
        Args:
            doc: PDFDocument to chunk
            
        Returns:
            List of chunks
        """
        chunks: List[Chunk] = []
        
        for page in doc.pages:
            if not page.text.strip():
                continue
            
            # Split page text
            page_chunks = self.splitter.split_text(page.text)
            
            for chunk_idx, chunk_text in enumerate(page_chunks):
                content = chunk_text.strip()
                if len(content) < MIN_CHUNK_LENGTH:
                    continue
                chunk_id = self._generate_chunk_id(
                    doc.doc_id,
                    page.page_num,
                    chunk_idx
                )
                chunk = Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    source_path=doc.source_path,
                    page_start=page.page_num,
                    page_end=page.page_num,
                    content=content,
                    content_type="text",
                    metadata={
                        "chunk_idx": chunk_idx,
                        "page_num": page.page_num,
                        "char_count": len(content)
                    }
                )
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from {doc.doc_id}")
        return chunks
    
    def chunk_multi_page(
        self,
        doc: PDFDocument,
        start_page: int,
        end_page: int,
        text: str
    ) -> List[Chunk]:
        """
        Chunk text that spans multiple pages
        
        Args:
            doc: Source document
            start_page: Starting page number
            end_page: Ending page number
            text: Text to chunk
            
        Returns:
            List of chunks
        """
        chunks: List[Chunk] = []
        
        text_chunks = self.splitter.split_text(text)
        
        for chunk_idx, chunk_text in enumerate(text_chunks):
            content = chunk_text.strip()
            if len(content) < MIN_CHUNK_LENGTH:
                continue
            chunk_id = self._generate_chunk_id(
                doc.doc_id,
                start_page,
                chunk_idx,
                suffix=f"_p{start_page}-{end_page}"
            )
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc.doc_id,
                source_path=doc.source_path,
                page_start=start_page,
                page_end=end_page,
                content=content,
                content_type="text",
                metadata={
                    "chunk_idx": chunk_idx,
                    "char_count": len(content),
                    "multi_page": True
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _generate_chunk_id(
        self,
        doc_id: str,
        page_num: int,
        chunk_idx: int,
        suffix: str = ""
    ) -> str:
        """Generate unique chunk ID (encode with replace so surrogates in doc_id don't crash)."""
        base = f"{doc_id}_p{page_num}_c{chunk_idx}{suffix}"
        hash_obj = hashlib.md5(base.encode("utf-8", errors="replace"))
        return f"{doc_id}_{hash_obj.hexdigest()[:8]}"
