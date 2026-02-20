"""
Main ingestion pipeline
Orchestrates PDF loading, chunking, and output
"""
from pathlib import Path
from typing import List
import json
from loguru import logger

from ragapp.ingest.loaders import PDFLoader, PAGE_RANGE_SIZE
from ragapp.ingest.chunkers import TextChunker, Chunk
from ragapp.ingest.tables import TableExtractor
from ragapp.ingest.figures import (
    extract_figures_from_pdf,
    figures_to_chunks,
    BlipFigureProcessor,
    OpenAIVisionFigureProcessor,
    DePlotFigureProcessor,
    FigureProcessor,
)


def _get_figure_processor(figure_model: str) -> FigureProcessor | None:
    if figure_model == "blip":
        return BlipFigureProcessor()
    if figure_model == "openai_vision":
        return OpenAIVisionFigureProcessor()
    if figure_model == "deplot":
        return DePlotFigureProcessor()
    logger.warning(f"Unknown figure_model={figure_model}, use 'blip', 'openai_vision', or 'deplot'")
    return None


def run_ingestion(
    input_dir: Path,
    output_file: Path,
    extract_tables: bool = True,
    table_format: str = "markdown",
    table_header_rows: int = 1,
    extract_figures: bool = False,
    figure_model: str = "blip",
) -> int:
    """
    Run full ingestion pipeline.

    Table chunks include structure metadata. If extract_figures=True, images are
    described with figure_model ('blip' or 'openai_vision') and stored as figure chunks.
    """
    logger.info(f"Starting ingestion pipeline")
    logger.info(f"Input: {input_dir}")
    logger.info(f"Output: {output_file}")

    pdf_loader = PDFLoader()
    text_chunker = TextChunker()
    table_extractor = (
        TableExtractor(output_format=table_format, header_rows=table_header_rows)
        if extract_tables
        else None
    )
    figure_processor: FigureProcessor | None = (
        _get_figure_processor(figure_model) if extract_figures else None
    )

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return 0

    total_files = len(pdf_files)
    logger.info(f"Found {total_files} PDF files")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    def _safe_utf8(s: str) -> str:
        return s.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")

    # Stream: per-PDF and within each PDF by page range (bounded memory for 1000+ PDFs and 300+ page PDFs)
    total_chunks = 0
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for idx, pdf_path in enumerate(pdf_files, start=1):
                try:
                    progress_pct = (idx / total_files) * 100
                    logger.info(
                        f"[{idx}/{total_files}] Processing ({progress_pct:.1f}%): {pdf_path.name}"
                    )
                    doc_id = pdf_path.stem
                    source_path = str(pdf_path)
                    total_pages = pdf_loader.get_page_count(pdf_path)

                    # Process one page range at a time so we never hold the full PDF in memory
                    for start in range(1, total_pages + 1, PAGE_RANGE_SIZE):
                        end = min(start + PAGE_RANGE_SIZE, total_pages + 1)
                        range_chunks: List[Chunk] = []

                        doc = pdf_loader.load_page_range(
                            pdf_path, start, end, doc_id=doc_id, total_pages=total_pages
                        )
                        if extract_tables and table_extractor:
                            tables = pdf_loader.get_tables_for_page_range(
                                pdf_path, start, end, doc_id
                            )
                            if tables:
                                range_chunks.extend(
                                    table_extractor.tables_to_chunks(
                                        tables, doc_id, source_path
                                    )
                                )
                        text_chunks = text_chunker.chunk_document(doc)
                        range_chunks.extend(text_chunks)

                        for chunk in range_chunks:
                            f.write(_safe_utf8(chunk.to_jsonl()) + "\n")
                        total_chunks += len(range_chunks)

                    # Figures: only for small PDFs to avoid loading full doc again; skip in streaming
                    if extract_figures and figure_processor and total_pages <= PAGE_RANGE_SIZE:
                        doc_full = pdf_loader.load(pdf_path)
                        figures = extract_figures_from_pdf(pdf_path)
                        if figures:
                            figure_chunks = figures_to_chunks(
                                figures, figure_processor, doc_full.doc_id, doc_full.source_path
                            )
                            for chunk in figure_chunks:
                                f.write(_safe_utf8(chunk.to_jsonl()) + "\n")
                            total_chunks += len(figure_chunks)
                            logger.info(f"Created {len(figure_chunks)} figure chunks from {pdf_path.name}")
                    elif extract_figures and total_pages > PAGE_RANGE_SIZE:
                        logger.debug(f"Skipping figures for large PDF {pdf_path.name} (streaming mode)")

                    logger.info(f"Created chunks from {pdf_path.name} (total so far: {total_chunks})")

                except Exception as e:
                    logger.error(f"Failed to process {pdf_path.name}: {e}")
                    continue
    except OSError as e:
        logger.error(f"Failed to write output file {output_file}: {e}")
        raise

    if total_chunks == 0:
        logger.warning("No chunks produced (all PDFs may have failed). Skipping write.")
        return 0

    logger.info(f"✅ Ingestion complete!")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Output: {output_file}")

    return total_chunks


def validate_chunks_file(chunks_file: Path) -> bool:
    """
    Validate chunks.jsonl file
    
    Args:
        chunks_file: Path to chunks.jsonl
        
    Returns:
        True if valid
    """
    logger.info(f"Validating {chunks_file}")
    
    required_fields = {
        "chunk_id", "doc_id", "source_path", "page_start", "page_end",
        "content", "content_type", "metadata"
    }
    
    valid_content_types = {"text", "table_md", "table_html", "figure"}
    
    try:
        with open(chunks_file, "r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, start=1):
                # Parse JSON
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Line {line_num}: Invalid JSON - {e}")
                    return False
                
                # Check required fields
                missing_fields = required_fields - set(chunk.keys())
                if missing_fields:
                    logger.error(f"Line {line_num}: Missing fields - {missing_fields}")
                    return False
                
                # Validate content_type
                if chunk["content_type"] not in valid_content_types:
                    logger.error(f"Line {line_num}: Invalid content_type - {chunk['content_type']}")
                    return False
                
                # Validate types
                if not isinstance(chunk["page_start"], int):
                    logger.error(f"Line {line_num}: page_start must be int")
                    return False
                
                if not isinstance(chunk["page_end"], int):
                    logger.error(f"Line {line_num}: page_end must be int")
                    return False
                
                if not isinstance(chunk["metadata"], dict):
                    logger.error(f"Line {line_num}: metadata must be dict")
                    return False
        
        logger.info(f"✅ Validation passed!")
        return True
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False
