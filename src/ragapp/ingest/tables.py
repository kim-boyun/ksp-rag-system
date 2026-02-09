"""
Table extraction and conversion
Converts PDF tables to Markdown or HTML with structure metadata and linearized text.
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from ragapp.ingest.chunkers import Chunk

# Type for 2D grid: cell can be str or None (merged cell)
TableGrid = List[List[Optional[str]]]


def _compute_merged_cells(grid: TableGrid) -> List[Dict[str, Any]]:
    """
    From a 2D grid (None = part of merged cell), compute rowspan/colspan for each origin cell.
    Returns list of {"row", "col", "rowspan", "colspan", "value"}.
    """
    if not grid:
        return []
    rows, cols = len(grid), max(len(r) for r in grid) if grid else 0
    result: List[Dict[str, Any]] = []

    for r in range(rows):
        for c in range(cols):
            if c >= len(grid[r]):
                continue
            val = grid[r][c]
            if val is None:
                continue
            # Origin cell: compute rowspan (consecutive Nones below) and colspan (consecutive Nones to the right)
            rowspan = 1
            for k in range(1, rows - r):
                if r + k < rows and c < len(grid[r + k]) and grid[r + k][c] is None:
                    rowspan += 1
                else:
                    break
            colspan = 1
            for k in range(1, cols - c):
                if c + k < len(grid[r]) and grid[r][c + k] is None:
                    colspan += 1
                else:
                    break
            result.append({
                "row": r,
                "col": c,
                "rowspan": rowspan,
                "colspan": colspan,
                "value": val.strip() if isinstance(val, str) else str(val),
            })
    return result


def _linearize_table(grid: TableGrid, header_rows: int = 1) -> str:
    """
    Produce a short linearized text for search: "컬럼: A, B, C. 행1: x, y, z. 행2: ..."
    """
    if not grid:
        return ""
    parts: List[str] = []
    # Header
    if header_rows > 0 and grid:
        header = grid[0]
        names = [str(cell or "").strip() for cell in header]
        if any(names):
            parts.append("컬럼: " + ", ".join(names) + ".")
    # Rows
    for i, row in enumerate(grid[header_rows:], start=1):
        cells = [str(cell or "").strip() for cell in row]
        if any(cells):
            parts.append(f"행{i}: " + ", ".join(cells) + ".")
    return " ".join(parts)


class TableExtractor:
    """
    Extract tables from PDFs and convert to structured format.
    Adds structure metadata (merged_cells, header_rows, column_names) and linearized text for search.
    """

    def __init__(self, output_format: str = "markdown", header_rows: int = 1):
        """
        Args:
            output_format: "markdown" or "html"
            header_rows: Number of header rows (default 1) for linearization and metadata
        """
        self.output_format = output_format
        self.header_rows = header_rows
        logger.info(f"TableExtractor initialized: format={output_format}, header_rows={header_rows}")

    def tables_to_chunks(
        self,
        tables: List[Dict[str, Any]],
        doc_id: str,
        source_path: str,
    ) -> List[Chunk]:
        """
        Convert extracted tables to chunks with structure metadata and linearized text.

        Args:
            tables: List of table dicts (table = 2D list, None = merged cell)
            doc_id: Document ID
            source_path: Source file path

        Returns:
            List of table chunks with enriched metadata
        """
        chunks: List[Chunk] = []

        for table_data in tables:
            page_num = table_data["page_num"]
            table_idx = table_data["table_idx"]
            grid: TableGrid = table_data["table"]

            if not grid:
                continue

            # Normalize grid: ensure list of list, handle None
            grid = [[c if c is not None else None for c in row] for row in grid]
            num_rows = len(grid)
            num_cols = max(len(r) for r in grid) if grid else 0

            # Structure metadata
            merged_cells = _compute_merged_cells(grid)
            column_names: List[str] = []
            if grid and num_cols:
                column_names = [str(grid[0][c] or "").strip() for c in range(min(len(grid[0]), num_cols))]
            linearized = _linearize_table(grid, self.header_rows)

            # Content: markdown or HTML (for display / LLM) + linearized for search
            if self.output_format == "markdown":
                content = self._table_to_markdown(grid)
                content_type = "table_md"
            else:
                content = self._table_to_html(grid)
                content_type = "table_html"
            if linearized.strip():
                content = content + "\n\n[선형화]\n" + linearized.strip()

            chunk_id = f"{doc_id}_table_p{page_num}_t{table_idx}"

            metadata: Dict[str, Any] = {
                "table_idx": table_idx,
                "page_num": page_num,
                "num_rows": num_rows,
                "num_cols": num_cols,
                "header_rows": self.header_rows,
                "column_names": column_names,
                "merged_cells": merged_cells,
                "linearized": linearized,
            }

            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                source_path=source_path,
                page_start=page_num,
                page_end=page_num,
                content=content,
                content_type=content_type,
                metadata=metadata,
            )
            chunks.append(chunk)

        logger.info(f"Converted {len(chunks)} tables to chunks (with structure metadata)")
        return chunks

    def _table_to_markdown(self, grid: TableGrid) -> str:
        """Convert table grid to Markdown (empty string for merged/None cells)."""
        if not grid or len(grid) < 2:
            return ""

        num_cols = max(len(r) for r in grid)
        header = (grid[0] + [None] * num_cols)[:num_cols]
        rows = grid[1:]

        md_lines = []
        md_lines.append("| " + " | ".join(str(cell or "") for cell in header) + " |")
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in rows:
            padded = (row + [None] * num_cols)[:num_cols]
            md_lines.append("| " + " | ".join(str(cell or "") for cell in padded) + " |")

        return "\n".join(md_lines)

    def _table_to_html(self, grid: TableGrid) -> str:
        """Convert table grid to HTML (empty cell for merged/None)."""
        if not grid:
            return ""

        num_cols = max(len(r) for r in grid)
        html_lines = ["<table>"]

        if len(grid) > 0:
            header = (grid[0] + [None] * num_cols)[:num_cols]
            html_lines.append("  <thead>")
            html_lines.append("    <tr>")
            for cell in header:
                html_lines.append(f"      <th>{cell or ''}</th>")
            html_lines.append("    </tr>")
            html_lines.append("  </thead>")

        if len(grid) > 1:
            html_lines.append("  <tbody>")
            for row in grid[1:]:
                padded = (row + [None] * num_cols)[:num_cols]
                html_lines.append("    <tr>")
                for cell in padded:
                    html_lines.append(f"      <td>{cell or ''}</td>")
                html_lines.append("    </tr>")
            html_lines.append("  </tbody>")

        html_lines.append("</table>")
        return "\n".join(html_lines)
