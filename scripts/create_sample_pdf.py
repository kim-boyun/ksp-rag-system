"""
Create sample PDF for testing ingestion pipeline
Run: python scripts/create_sample_pdf.py
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from pathlib import Path


def create_sample_pdf(output_path: Path):
    """Create a sample PDF with text and tables"""
    
    # Create PDF
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=30,
        alignment=1  # Center
    )
    story.append(Paragraph("RAG System Test Document", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Introduction
    story.append(Paragraph("1. Introduction", styles['Heading2']))
    intro_text = """
    RAG (Retrieval-Augmented Generation) is a hybrid approach that combines 
    information retrieval with large language models. This document serves as 
    a test case for the PDF ingestion pipeline.
    """
    story.append(Paragraph(intro_text, styles['BodyText']))
    story.append(Spacer(1, 0.2*inch))
    
    # Section 2
    story.append(Paragraph("2. Key Concepts", styles['Heading2']))
    concepts_text = """
    The RAG system consists of several key components:
    <br/><br/>
    <b>Retrieval:</b> Finding relevant documents from a knowledge base using 
    keyword search (BM25) or semantic search (dense vectors).
    <br/><br/>
    <b>Augmentation:</b> Combining retrieved context with user queries to 
    create enriched prompts for language models.
    <br/><br/>
    <b>Generation:</b> Using LLMs to generate contextually relevant responses 
    based on the augmented prompt.
    """
    story.append(Paragraph(concepts_text, styles['BodyText']))
    story.append(Spacer(1, 0.3*inch))
    
    # Table
    story.append(Paragraph("3. Comparison Table", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    table_data = [
        ['Method', 'Precision', 'Recall', 'F1-Score'],
        ['BM25', '0.72', '0.68', '0.70'],
        ['Dense Retrieval', '0.78', '0.75', '0.76'],
        ['Hybrid (BM25+Dense)', '0.85', '0.82', '0.83']
    ]
    
    table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#EFF6FF')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # Section 4
    story.append(Paragraph("4. Implementation Details", styles['Heading2']))
    impl_text = """
    Our implementation uses Docker containers for consistent deployment across 
    development and production environments. The system supports two modes:
    <br/><br/>
    <b>Local Mode:</b> Uses BM25 and FAISS for retrieval, with OpenAI API for 
    generation. Suitable for development and testing.
    <br/><br/>
    <b>Server Mode:</b> Leverages Elasticsearch for hybrid search and vLLM for 
    local LLM inference on GPU servers. Optimized for production workloads.
    """
    story.append(Paragraph(impl_text, styles['BodyText']))
    story.append(Spacer(1, 0.3*inch))
    
    # Conclusion
    story.append(Paragraph("5. Conclusion", styles['Heading2']))
    conclusion_text = """
    This document demonstrates the PDF ingestion pipeline's ability to extract 
    text, tables, and metadata. The chunking system preserves semantic boundaries 
    while maintaining efficient retrieval performance.
    """
    story.append(Paragraph(conclusion_text, styles['BodyText']))
    
    # Build PDF
    doc.build(story)
    print(f"✅ Created sample PDF: {output_path}")


if __name__ == "__main__":
    output_path = Path("data/raw/sample_rag_document.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        create_sample_pdf(output_path)
    except ImportError:
        print("❌ Error: reportlab not installed")
        print("Install with: pip install reportlab")
        print("\nAlternatively, create a PDF manually and place it in data/raw/")
