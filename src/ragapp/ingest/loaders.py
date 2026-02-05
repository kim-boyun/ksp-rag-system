"""
PDF document loaders
Extracts text and metadata from PDF files
"""
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import pypdf
import pdfplumber
from loguru import logger


@dataclass
class PDFPage:
    """Single page from PDF with metadata"""
    page_num: int
    text: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PDFDocument:
    """Complete PDF document"""
    doc_id: str
    source_path: str
    pages: List[PDFPage]
    total_pages: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "source_path": self.source_path,
            "pages": [p.to_dict() for p in self.pages],
            "total_pages": self.total_pages,
            "metadata": self.metadata
        }


class PDFLoader:
    """
    PDF document loader
    Extracts text page-by-page with metadata
    """
    
    def __init__(self):
        pass
    
    def load(self, pdf_path: Path) -> PDFDocument:
        """
        Load PDF and extract text from all pages
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            PDFDocument with extracted text
        """
        logger.info(f"Loading PDF: {pdf_path}")
        
        doc_id = pdf_path.stem
        pages: List[PDFPage] = []
        
        # Use pypdf for basic text extraction
        with open(pdf_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            
            # Extract metadata
            metadata = self._extract_metadata(pdf_reader)
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text() or ""
                
                page_obj = PDFPage(
                    page_num=page_num,
                    text=text.strip(),
                    metadata={
                        "page_num": page_num,
                        "char_count": len(text)
                    }
                )
                pages.append(page_obj)
        
        logger.info(f"Extracted {len(pages)} pages from {pdf_path.name}")
        
        return PDFDocument(
            doc_id=doc_id,
            source_path=str(pdf_path),
            pages=pages,
            total_pages=total_pages,
            metadata=metadata
        )
    
    def load_with_tables(self, pdf_path: Path) -> tuple[PDFDocument, List[Dict[str, Any]]]:
        """
        Load PDF and extract both text and tables
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (PDFDocument, list of tables)
        """
        # Load text first
        doc = self.load(pdf_path)
        
        # Extract tables using pdfplumber
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(page_tables):
                        if table:
                            tables.append({
                                "page_num": page_num,
                                "table_idx": table_idx,
                                "table": table,
                                "doc_id": doc.doc_id
                            })
            
            logger.info(f"Extracted {len(tables)} tables from {pdf_path.name}")
        except Exception as e:
            logger.warning(f"Failed to extract tables from {pdf_path.name}: {e}")
        
        return doc, tables
    
    def _extract_metadata(self, pdf_reader: pypdf.PdfReader) -> Dict[str, Any]:
        """Extract PDF metadata"""
        metadata = {}
        
        if pdf_reader.metadata:
            try:
                metadata["title"] = pdf_reader.metadata.get("/Title", "")
                metadata["author"] = pdf_reader.metadata.get("/Author", "")
                metadata["subject"] = pdf_reader.metadata.get("/Subject", "")
                metadata["creator"] = pdf_reader.metadata.get("/Creator", "")
            except Exception as e:
                logger.warning(f"Failed to extract metadata: {e}")
        
        return metadata
