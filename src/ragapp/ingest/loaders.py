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


def _safe_utf8(s: str) -> str:
    """Replace surrogates/invalid chars so UTF-8 encode never fails downstream."""
    return s.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


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


# 페이지 범위 단위로 로드할 때 한 번에 넣을 페이지 수 (대용량 PDF 메모리 절약)
PAGE_RANGE_SIZE = 50


class PDFLoader:
    """
    PDF document loader
    Extracts text page-by-page with metadata
    """
    
    def __init__(self):
        pass
    
    def get_page_count(self, pdf_path: Path) -> int:
        """Return total number of pages without loading full document."""
        with open(pdf_path, "rb") as f:
            return len(pypdf.PdfReader(f).pages)
    
    def load_page_range(
        self,
        pdf_path: Path,
        start_page: int,
        end_page: int,
        doc_id: str | None = None,
        total_pages: int | None = None,
    ) -> PDFDocument:
        """
        Load only the given page range (1-based, end_page exclusive).
        E.g. start_page=1, end_page=51 loads pages 1..50.
        Use for memory-efficient streaming of large PDFs.
        """
        doc_id = doc_id or pdf_path.stem
        with open(pdf_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            if total_pages is None:
                total_pages = len(pdf_reader.pages)
            metadata = self._extract_metadata(pdf_reader)
            pages: List[PDFPage] = []
            for page_num in range(start_page, min(end_page, total_pages + 1)):
                page = pdf_reader.pages[page_num - 1]
                raw = page.extract_text() or ""
                text = _safe_utf8(raw).strip()
                pages.append(
                    PDFPage(
                        page_num=page_num,
                        text=text,
                        metadata={"page_num": page_num, "char_count": len(text)},
                    )
                )
        return PDFDocument(
            doc_id=doc_id,
            source_path=str(pdf_path),
            pages=pages,
            total_pages=total_pages,
            metadata=metadata,
        )
    
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
                raw = page.extract_text() or ""
                text = _safe_utf8(raw).strip()

                page_obj = PDFPage(
                    page_num=page_num,
                    text=text,
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
    
    def load_with_tables(
        self,
        pdf_path: Path,
        table_settings: Dict[str, Any] | None = None,
    ) -> tuple[PDFDocument, List[Dict[str, Any]]]:
        """
        Load PDF and extract both text and tables.
        Uses find_tables() so that merged cells are represented as None in the grid,
        preserving structure for downstream processing.

        Args:
            pdf_path: Path to PDF file
            table_settings: Optional pdfplumber table finder settings (e.g. strategy)

        Returns:
            Tuple of (PDFDocument, list of tables).
            Each table dict: page_num, table_idx, table (2D list, None = merged cell), doc_id
        """
        doc = self.load(pdf_path)
        tables: List[Dict[str, Any]] = []

        def append_table(pg: int, idx: int, grid: List) -> None:
            tables.append({
                "page_num": pg,
                "table_idx": idx,
                "table": grid,
                "doc_id": doc.doc_id,
            })

        try:
            with pdfplumber.open(pdf_path) as pdf:
                # 문서당 첫 페이지만 find_tables() 시도 → 지원 여부에 따라 경로 결정
                use_find_tables: bool | None = None

                for page_num, page in enumerate(pdf.pages, start=1):
                    if use_find_tables is None:
                        try:
                            finder = page.find_tables()
                            for table_idx, tbl in enumerate(finder.tables):
                                grid = tbl.extract()
                                if not grid:
                                    continue
                                append_table(page_num, table_idx, grid)
                            use_find_tables = True
                        except Exception as e:
                            logger.debug(
                                "find_tables not available (%s), using extract_tables for %s",
                                e,
                                pdf_path.name,
                            )
                            use_find_tables = False
                            for table_idx, table in enumerate(page.extract_tables() or []):
                                if table:
                                    append_table(page_num, table_idx, table)
                    elif use_find_tables:
                        finder = page.find_tables()
                        for table_idx, tbl in enumerate(finder.tables):
                            grid = tbl.extract()
                            if not grid:
                                continue
                            append_table(page_num, table_idx, grid)
                    else:
                        for table_idx, table in enumerate(page.extract_tables() or []):
                            if table:
                                append_table(page_num, table_idx, table)

            logger.info(f"Extracted {len(tables)} tables from {pdf_path.name}")
        except Exception as e:
            logger.warning(f"Failed to extract tables from {pdf_path.name}: {e}")

        return doc, tables
    
    def get_tables_for_page_range(
        self,
        pdf_path: Path,
        start_page: int,
        end_page: int,
        doc_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract tables only for pages in [start_page, end_page) (1-based, end exclusive).
        Use for memory-efficient streaming; does not load full document.
        """
        tables: List[Dict[str, Any]] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                use_find_tables: bool | None = None
                for page_num in range(start_page, min(end_page, len(pdf.pages) + 1)):
                    page = pdf.pages[page_num - 1]
                    if use_find_tables is None:
                        try:
                            finder = page.find_tables()
                            for table_idx, tbl in enumerate(finder.tables):
                                grid = tbl.extract()
                                if grid:
                                    tables.append({
                                        "page_num": page_num,
                                        "table_idx": table_idx,
                                        "table": grid,
                                        "doc_id": doc_id,
                                    })
                            use_find_tables = True
                        except Exception:
                            use_find_tables = False
                            for table_idx, table in enumerate(page.extract_tables() or []):
                                if table:
                                    tables.append({
                                        "page_num": page_num,
                                        "table_idx": table_idx,
                                        "table": table,
                                        "doc_id": doc_id,
                                    })
                    elif use_find_tables:
                        finder = page.find_tables()
                        for table_idx, tbl in enumerate(finder.tables):
                            grid = tbl.extract()
                            if grid:
                                tables.append({
                                    "page_num": page_num,
                                    "table_idx": table_idx,
                                    "table": grid,
                                    "doc_id": doc_id,
                                })
                    else:
                        for table_idx, table in enumerate(page.extract_tables() or []):
                            if table:
                                tables.append({
                                    "page_num": page_num,
                                    "table_idx": table_idx,
                                    "table": table,
                                    "doc_id": doc_id,
                                })
        except Exception as e:
            logger.warning(f"Failed to extract tables for pages {start_page}-{end_page} from {pdf_path.name}: {e}")
        return tables
    
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
