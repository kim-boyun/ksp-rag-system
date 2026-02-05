"""
Table extraction and conversion
Converts PDF tables to Markdown or HTML format
"""
from typing import List, Dict, Any
from loguru import logger

from ragapp.ingest.chunkers import Chunk


class TableExtractor:
    """
    Extract tables from PDFs and convert to structured format
    """
    
    def __init__(self, output_format: str = "markdown"):
        """
        Args:
            output_format: "markdown" or "html"
        """
        self.output_format = output_format
        logger.info(f"TableExtractor initialized: format={output_format}")
    
    def tables_to_chunks(
        self,
        tables: List[Dict[str, Any]],
        doc_id: str,
        source_path: str
    ) -> List[Chunk]:
        """
        Convert extracted tables to chunks
        
        Args:
            tables: List of tables from PDFLoader
            doc_id: Document ID
            source_path: Source file path
            
        Returns:
            List of table chunks
        """
        chunks: List[Chunk] = []
        
        for table_data in tables:
            page_num = table_data["page_num"]
            table_idx = table_data["table_idx"]
            table = table_data["table"]
            
            # Convert to markdown or HTML
            if self.output_format == "markdown":
                content = self._table_to_markdown(table)
                content_type = "table_md"
            else:
                content = self._table_to_html(table)
                content_type = "table_html"
            
            chunk_id = f"{doc_id}_table_p{page_num}_t{table_idx}"
            
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                source_path=source_path,
                page_start=page_num,
                page_end=page_num,
                content=content,
                content_type=content_type,
                metadata={
                    "table_idx": table_idx,
                    "page_num": page_num,
                    "num_rows": len(table),
                    "num_cols": len(table[0]) if table else 0
                }
            )
            chunks.append(chunk)
        
        logger.info(f"Converted {len(chunks)} tables to chunks")
        return chunks
    
    def _table_to_markdown(self, table: List[List[str]]) -> str:
        """Convert table to Markdown format"""
        if not table or len(table) < 2:
            return ""
        
        # First row as header
        header = table[0]
        rows = table[1:]
        
        # Build markdown
        md_lines = []
        
        # Header row
        md_lines.append("| " + " | ".join(str(cell or "") for cell in header) + " |")
        
        # Separator
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")
        
        # Data rows
        for row in rows:
            md_lines.append("| " + " | ".join(str(cell or "") for cell in row) + " |")
        
        return "\n".join(md_lines)
    
    def _table_to_html(self, table: List[List[str]]) -> str:
        """Convert table to HTML format"""
        if not table:
            return ""
        
        html_lines = ["<table>"]
        
        # First row as header
        if len(table) > 0:
            html_lines.append("  <thead>")
            html_lines.append("    <tr>")
            for cell in table[0]:
                html_lines.append(f"      <th>{cell or ''}</th>")
            html_lines.append("    </tr>")
            html_lines.append("  </thead>")
        
        # Data rows
        if len(table) > 1:
            html_lines.append("  <tbody>")
            for row in table[1:]:
                html_lines.append("    <tr>")
                for cell in row:
                    html_lines.append(f"      <td>{cell or ''}</td>")
                html_lines.append("    </tr>")
            html_lines.append("  </tbody>")
        
        html_lines.append("</table>")
        
        return "\n".join(html_lines)
