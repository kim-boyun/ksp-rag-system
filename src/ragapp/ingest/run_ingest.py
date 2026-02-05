"""
Main ingestion pipeline
Orchestrates PDF loading, chunking, and output
"""
from pathlib import Path
from typing import List
import json
from loguru import logger

from ragapp.ingest.loaders import PDFLoader
from ragapp.ingest.chunkers import TextChunker, Chunk
from ragapp.ingest.tables import TableExtractor


def run_ingestion(
    input_dir: Path,
    output_file: Path,
    extract_tables: bool = True,
    table_format: str = "markdown"
) -> int:
    """
    Run full ingestion pipeline
    
    Args:
        input_dir: Directory containing PDF files
        output_file: Output JSONL file path
        extract_tables: Whether to extract tables
        table_format: Table output format ("markdown" or "html")
        
    Returns:
        Number of chunks created
    """
    logger.info(f"Starting ingestion pipeline")
    logger.info(f"Input: {input_dir}")
    logger.info(f"Output: {output_file}")
    
    # Initialize components
    pdf_loader = PDFLoader()
    text_chunker = TextChunker()
    table_extractor = TableExtractor(output_format=table_format) if extract_tables else None
    
    # Find all PDF files
    pdf_files = sorted(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return 0
    
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    # Process each PDF
    all_chunks: List[Chunk] = []
    
    for pdf_path in pdf_files:
        try:
            logger.info(f"Processing: {pdf_path.name}")
            
            # Load PDF
            if extract_tables and table_extractor:
                doc, tables = pdf_loader.load_with_tables(pdf_path)
                
                # Convert tables to chunks
                table_chunks = table_extractor.tables_to_chunks(
                    tables,
                    doc.doc_id,
                    doc.source_path
                )
                all_chunks.extend(table_chunks)
            else:
                doc = pdf_loader.load(pdf_path)
            
            # Chunk text
            text_chunks = text_chunker.chunk_document(doc)
            all_chunks.extend(text_chunks)
            
            logger.info(f"Created {len(text_chunks)} text chunks from {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            continue
    
    # Write to JSONL
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(chunk.to_jsonl() + "\n")
    
    logger.info(f"✅ Ingestion complete!")
    logger.info(f"Total chunks: {len(all_chunks)}")
    logger.info(f"Output: {output_file}")
    
    return len(all_chunks)


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
    
    valid_content_types = {"text", "table_md", "table_html"}
    
    try:
        with open(chunks_file, 'r', encoding='utf-8') as f:
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
