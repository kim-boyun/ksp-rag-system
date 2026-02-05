"""
Ingestion pipeline tests
"""
import json
from pathlib import Path
import pytest

from ragapp.ingest.loaders import PDFLoader, PDFDocument
from ragapp.ingest.chunkers import TextChunker, Chunk
from ragapp.ingest.tables import TableExtractor


def test_chunk_schema():
    """Test chunk has all required fields"""
    chunk = Chunk(
        chunk_id="test_chunk_001",
        doc_id="test_doc",
        source_path="/path/to/doc.pdf",
        page_start=1,
        page_end=1,
        content="This is test content.",
        content_type="text",
        metadata={"test": "value"}
    )
    
    # Test to_dict
    chunk_dict = chunk.to_dict()
    
    required_fields = {
        "chunk_id", "doc_id", "source_path", "page_start", "page_end",
        "content", "content_type", "metadata"
    }
    
    assert set(chunk_dict.keys()) == required_fields
    assert chunk_dict["chunk_id"] == "test_chunk_001"
    assert chunk_dict["content_type"] == "text"
    assert isinstance(chunk_dict["metadata"], dict)


def test_chunk_jsonl_format():
    """Test chunk serializes to valid JSONL"""
    chunk = Chunk(
        chunk_id="test_chunk_002",
        doc_id="test_doc",
        source_path="/path/to/doc.pdf",
        page_start=1,
        page_end=2,
        content="Multi-page content.",
        content_type="text",
        metadata={"pages": 2}
    )
    
    jsonl_line = chunk.to_jsonl()
    
    # Should be valid JSON
    parsed = json.loads(jsonl_line)
    
    assert parsed["chunk_id"] == "test_chunk_002"
    assert parsed["page_start"] == 1
    assert parsed["page_end"] == 2
    assert parsed["content_type"] == "text"


def test_text_chunker_initialization():
    """Test TextChunker initializes correctly"""
    chunker = TextChunker(chunk_size=512, chunk_overlap=50)
    
    assert chunker.chunk_size == 512
    assert chunker.chunk_overlap == 50
    assert chunker.splitter is not None


def test_table_to_markdown():
    """Test table conversion to markdown"""
    extractor = TableExtractor(output_format="markdown")
    
    table = [
        ["Header 1", "Header 2", "Header 3"],
        ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
        ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
    ]
    
    md = extractor._table_to_markdown(table)
    
    assert "| Header 1 | Header 2 | Header 3 |" in md
    assert "| --- | --- | --- |" in md
    assert "Row 1 Col 1" in md


def test_table_to_html():
    """Test table conversion to HTML"""
    extractor = TableExtractor(output_format="html")
    
    table = [
        ["Name", "Age"],
        ["Alice", "30"],
        ["Bob", "25"]
    ]
    
    html = extractor._table_to_html(table)
    
    assert "<table>" in html
    assert "<thead>" in html
    assert "<th>Name</th>" in html
    assert "<td>Alice</td>" in html
    assert "</table>" in html


def test_validate_chunks_file_schema(tmp_path):
    """Test validation of chunks.jsonl schema"""
    from ragapp.ingest.run_ingest import validate_chunks_file
    
    # Create valid chunks file
    chunks_file = tmp_path / "chunks.jsonl"
    
    chunks = [
        {
            "chunk_id": "chunk_001",
            "doc_id": "doc_001",
            "source_path": "/test/doc.pdf",
            "page_start": 1,
            "page_end": 1,
            "content": "Test content",
            "content_type": "text",
            "metadata": {"test": True}
        },
        {
            "chunk_id": "chunk_002",
            "doc_id": "doc_001",
            "source_path": "/test/doc.pdf",
            "page_start": 2,
            "page_end": 2,
            "content": "| Header | Value |\n| --- | --- |",
            "content_type": "table_md",
            "metadata": {"table_idx": 0}
        }
    ]
    
    with open(chunks_file, 'w') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")
    
    # Should validate successfully
    assert validate_chunks_file(chunks_file) is True


def test_validate_chunks_file_missing_field(tmp_path):
    """Test validation fails with missing field"""
    from ragapp.ingest.run_ingest import validate_chunks_file
    
    chunks_file = tmp_path / "invalid_chunks.jsonl"
    
    # Missing 'content_type' field
    invalid_chunk = {
        "chunk_id": "chunk_001",
        "doc_id": "doc_001",
        "source_path": "/test/doc.pdf",
        "page_start": 1,
        "page_end": 1,
        "content": "Test",
        "metadata": {}
    }
    
    with open(chunks_file, 'w') as f:
        f.write(json.dumps(invalid_chunk) + "\n")
    
    # Should fail validation
    assert validate_chunks_file(chunks_file) is False


def test_content_type_validation(tmp_path):
    """Test content_type must be valid"""
    from ragapp.ingest.run_ingest import validate_chunks_file
    
    chunks_file = tmp_path / "chunks.jsonl"
    
    # Invalid content_type
    chunk = {
        "chunk_id": "chunk_001",
        "doc_id": "doc_001",
        "source_path": "/test/doc.pdf",
        "page_start": 1,
        "page_end": 1,
        "content": "Test",
        "content_type": "invalid_type",  # Should be text, table_md, or table_html
        "metadata": {}
    }
    
    with open(chunks_file, 'w') as f:
        f.write(json.dumps(chunk) + "\n")
    
    # Should fail validation
    assert validate_chunks_file(chunks_file) is False
