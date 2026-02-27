"""
CLI interface using Typer
"""
import sys
from typing import Optional
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from loguru import logger

from ragapp.config import get_config
from ragapp.pipeline.rag_pipeline import RAGPipeline

app = typer.Typer(
    name="ragapp",
    help="Docker-based hybrid RAG system",
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False
)
console = Console()


@app.command()
def ask(
    query: str = typer.Argument(..., help="Question to ask the RAG system"),
    rerank: bool = typer.Option(False, help="Enable LLM-based reranking"),
    output: str = typer.Option(None, help="Save response to file (JSON format)")
):
    """
    Ask a question to the RAG system (full pipeline: retrieve + rerank + generate)
    
    Uses retriever mode from config (RETRIEVER_MODE in .env)
    
    Example:
        # Local mode (default)
        docker compose --profile local run --rm app python -m ragapp ask "What is RAG?"
        
        # Elasticsearch mode (set RETRIEVER_MODE=elastic in .env)
        docker compose --profile server run --rm app python -m ragapp ask "What is RAG?"
        
        # With reranking
        docker compose --profile local run --rm app python -m ragapp ask "온두라스 연금 시스템은?" --rerank
    """
    from pathlib import Path
    
    config = get_config()
    
    # Display configuration
    console.print(Panel.fit(
        f"[bold cyan]Mode:[/bold cyan] {config.mode}\n"
        f"[bold cyan]Retriever:[/bold cyan] {config.retriever_mode} ({config.get_retriever_type()})\n"
        f"[bold cyan]LLM Provider:[/bold cyan] {config.llm_provider}\n"
        f"[bold cyan]Rerank:[/bold cyan] {rerank}",
        title="🚀 RAG Configuration"
    ))
    
    try:
        # Initialize pipeline
        with console.status("[bold green]Initializing pipeline..."):
            pipeline = RAGPipeline(use_rerank=rerank)
        
        # Process query
        with console.status("[bold green]Processing query..."):
            response = pipeline.ask(query, use_rerank=rerank)
        
        # Extract citations
        from ragapp.prompts import extract_citations
        citations = extract_citations(response.answer, response.retrieved_docs)
        
        # Save to file if requested
        if output:
            import json
            output_data = {
                "query": query,
                "answer": response.answer,
                "citations": citations,
                "documents": [
                    {
                        "rank": i,
                        "score": doc.score,
                        "doc_id": doc.metadata.get('doc_id', 'N/A'),
                        "page_num": doc.metadata.get('page_num', 'N/A'),
                        "chunk_id": doc.metadata.get('chunk_id', 'N/A'),
                        "content_type": doc.metadata.get('content_type', 'text'),
                        "content": doc.content,
                        "metadata": doc.metadata
                    }
                    for i, doc in enumerate(response.retrieved_docs, 1)
                ],
                "metadata": response.metadata
            }
            
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            console.print(f"\n[bold green]✅ Response saved to:[/bold green] {output}")
        
        # Display results
        console.print("\n[bold green]📄 Retrieved Documents:[/bold green]")
        
        for i, doc in enumerate(response.retrieved_docs, 1):
            content_preview = doc.content[:150] + "..." if len(doc.content) > 150 else doc.content
            doc_id = doc.metadata.get('doc_id', 'N/A')
            
            # Truncate long doc_id
            if len(doc_id) > 60:
                doc_id = doc_id[:57] + "..."
            
            score_display = f"Score: {doc.score:.4f}"
            if 'rerank_score' in doc.metadata:
                score_display = f"Rerank: {doc.score:.4f}"
            
            console.print(f"\n[bold cyan]#{i}[/bold cyan] [dim]({score_display})[/dim]")
            console.print(f"[yellow]Doc:[/yellow] {doc_id}")
            console.print(f"{content_preview}")
        
        console.print("\n" + "═" * 80)
        console.print("\n[bold green]💬 Answer:[/bold green]")
        console.print(Panel(response.answer, border_style="green"))
        
        # Display citations
        if citations:
            console.print("\n[bold cyan]📚 Citations:[/bold cyan]")
            for cite in citations:
                console.print(
                    f"  • 문서 {cite['doc_num']}: {cite['doc_id']} "
                    f"(페이지: {cite['page_num']}, 유형: {cite['content_type']})"
                )
        
        console.print(f"\n[dim]Metadata: {response.metadata}[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        logger.exception("Pipeline failed")
        raise typer.Exit(1)


@app.command()
def config():
    """
    Display current configuration
    """
    cfg = get_config()
    
    console.print("\n[bold cyan]🔧 Configuration[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", width=60)
    
    table.add_row("Mode", cfg.mode)
    table.add_row("Retriever Type", cfg.get_retriever_type())
    table.add_row("LLM Endpoint", cfg.get_llm_endpoint())
    table.add_row("Top K", str(cfg.top_k))
    table.add_row("Rerank Top K", str(cfg.rerank_top_k))
    table.add_row("Chunk Size", str(cfg.chunk_size))
    table.add_row("Log Level", cfg.log_level)
    
    if cfg.is_local_mode:
        table.add_row("Local Embedding Model", cfg.local_embedding_model)
        table.add_row("LLM Model", cfg.llm_model)
    else:
        table.add_row("Elastic Host", f"{cfg.elastic_host}:{cfg.elastic_port}")
        table.add_row("Elastic Index", cfg.elastic_index_name)
        table.add_row("Server LLM Model", cfg.server_llm_model)
    
    console.print(table)


@app.command()
def ingest(
    input_dir: str = typer.Option("data/raw", help="Input directory with PDF files"),
    output: str = typer.Option("data/processed/chunks.jsonl", help="Output JSONL file"),
    tables: bool = typer.Option(True, help="Extract tables from PDFs"),
    table_format: str = typer.Option("markdown", help="Table format: markdown or html"),
    table_header_rows: int = typer.Option(1, help="Number of header rows for table structure metadata"),
    figures: Optional[bool] = typer.Option(None, "--figures/--no-figures", help="Extract figures/charts. Default: from EXTRACT_FIGURES env (false = text+table only)"),
    figure_model: str = typer.Option("blip", help="Figure model: blip, openai_vision, or deplot (chart-to-text)"),
    validate: bool = typer.Option(True, help="Validate output file")
):
    """
    Ingest PDF documents and create chunks.
    Table chunks include structure metadata. Use --figures to add figure/chart descriptions.
    """
    from ragapp.ingest.run_ingest import run_ingestion, validate_chunks_file

    if figures is None:
        figures = get_config().extract_figures

    console.print(Panel.fit(
        f"[bold cyan]Input:[/bold cyan] {input_dir}\n"
        f"[bold cyan]Output:[/bold cyan] {output}\n"
        f"[bold cyan]Extract Tables:[/bold cyan] {tables}\n"
        f"[bold cyan]Table Format:[/bold cyan] {table_format}\n"
        f"[bold cyan]Table Header Rows:[/bold cyan] {table_header_rows}\n"
        f"[bold cyan]Extract Figures:[/bold cyan] {figures}\n"
        f"[bold cyan]Figure Model:[/bold cyan] {figure_model}",
        title="📥 Ingestion Pipeline"
    ))

    input_path = Path(input_dir)
    output_path = Path(output)

    if not input_path.exists():
        console.print(f"[bold red]Error:[/bold red] Input directory not found: {input_dir}")
        raise typer.Exit(1)

    with console.status("[bold green]Processing PDFs..."):
        num_chunks = run_ingestion(
            input_dir=input_path,
            output_file=output_path,
            extract_tables=tables,
            table_format=table_format,
            table_header_rows=table_header_rows,
            extract_figures=figures,
            figure_model=figure_model,
        )
    
    console.print(f"\n[bold green]✅ Ingestion complete![/bold green]")
    console.print(f"Created {num_chunks} chunks")
    console.print(f"Output: {output_path}")
    
    # Validate output
    if validate and num_chunks > 0:
        console.print(f"\n[bold cyan]Validating output...[/bold cyan]")
        if validate_chunks_file(output_path):
            console.print("[bold green]✅ Validation passed![/bold green]")
        else:
            console.print("[bold red]❌ Validation failed![/bold red]")
            raise typer.Exit(1)


@app.command()
def index(
    chunks: str = typer.Option("data/processed/chunks.jsonl", help="Input chunks file"),
    output: str = typer.Option("data/index", help="Output index directory"),
    model: str = typer.Option("BAAI/bge-m3", help="BGE embedding model"),
    batch_size: int = typer.Option(32, help="Batch size for embedding")
):
    """
    Build local hybrid index (BM25 + FAISS)
    
    Example:
        docker compose --profile local run --rm app python -m ragapp index
        docker compose --profile local run --rm app python -m ragapp index --chunks data/processed/chunks.jsonl
    """
    from ragapp.index.build_local_index import build_local_index
    
    console.print(Panel.fit(
        f"[bold cyan]Chunks:[/bold cyan] {chunks}\n"
        f"[bold cyan]Output:[/bold cyan] {output}\n"
        f"[bold cyan]Model:[/bold cyan] {model}\n"
        f"[bold cyan]Batch Size:[/bold cyan] {batch_size}",
        title="🔨 Building Local Index"
    ))
    
    chunks_path = Path(chunks)
    output_path = Path(output)
    
    if not chunks_path.exists():
        console.print(f"[bold red]Error:[/bold red] Chunks file not found: {chunks}")
        raise typer.Exit(1)
    
    try:
        metadata = build_local_index(
            chunks_file=chunks_path,
            output_dir=output_path,
            embedding_model=model,
            batch_size=batch_size
        )
        
        console.print(f"\n[bold green]✅ Index built successfully![/bold green]")
        console.print(f"Location: {output_path}")
        console.print(f"Chunks indexed: {metadata['num_chunks']}")
        console.print(f"Embedding dimension: {metadata['embedding_dimension']}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def index_elastic(
    chunks: str = typer.Option("data/processed/chunks.jsonl", help="Input chunks file"),
    host: str = typer.Option(None, help="Elasticsearch host (default: from config)"),
    port: int = typer.Option(None, help="Elasticsearch port (default: from config)"),
    index_name: str = typer.Option(None, help="Index name (default: from config)"),
    model: str = typer.Option("BAAI/bge-m3", help="BGE embedding model"),
    batch_size: int = typer.Option(32, help="Batch size for embedding"),
    index_batch_size: int = typer.Option(None, help="Chunks per streaming batch (default: 3000 for bge-m3, 10000 else; reduce if OOM)"),
    recreate: bool = typer.Option(False, help="Recreate index if exists")
):
    """
    Build Elasticsearch hybrid index
    
    Example:
        docker compose --profile server run --rm app python -m ragapp index-elastic
        docker compose --profile server run --rm app python -m ragapp index-elastic --recreate
    """
    from ragapp.index.build_elastic_index import build_elastic_index
    
    # Load config for defaults
    config = get_config()
    
    if host is None:
        host = config.elastic_host
    if port is None:
        port = config.elastic_port
    if index_name is None:
        index_name = config.elastic_index_name
    
    console.print(Panel.fit(
        f"[bold cyan]Chunks:[/bold cyan] {chunks}\n"
        f"[bold cyan]Elasticsearch:[/bold cyan] {host}:{port}\n"
        f"[bold cyan]Index:[/bold cyan] {index_name}\n"
        f"[bold cyan]Model:[/bold cyan] {model}\n"
        f"[bold cyan]Batch Size:[/bold cyan] {batch_size}\n"
        f"[bold cyan]Recreate:[/bold cyan] {recreate}",
        title="🔨 Building Elasticsearch Index"
    ))
    
    chunks_path = Path(chunks)
    
    if not chunks_path.exists():
        console.print(f"[bold red]Error:[/bold red] Chunks file not found: {chunks}")
        raise typer.Exit(1)
    
    try:
        build_elastic_index(
            chunks_file=str(chunks_path),
            elastic_host=host,
            elastic_port=port,
            index_name=index_name,
            embedding_model=model,
            batch_size=batch_size,
            index_batch_size=index_batch_size,
            recreate=recreate
        )
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def retrieve(
    query: str = typer.Argument(..., help="Search query"),
    mode: str = typer.Option(None, help="Retriever mode: local or elastic (default: from config)"),
    index_dir: str = typer.Option("data/index", help="Index directory (for local mode)"),
    top_n: int = typer.Option(None, help="Number of results before reranking (default: from config)"),
    rerank: bool = typer.Option(False, help="Enable LLM-based reranking"),
    top_k: int = typer.Option(None, help="Number of results after reranking (default: from config)"),
    output: str = typer.Option(None, help="Save results to file (JSON format)")
):
    """
    Retrieve documents using hybrid search (local or Elasticsearch)
    
    Example:
        # Local mode
        docker compose --profile local run --rm app python -m ragapp retrieve "What is RAG?"
        
        # Elasticsearch mode
        docker compose --profile server run --rm app python -m ragapp retrieve "What is RAG?" --mode elastic
        
        # With reranking
        docker compose --profile local run --rm app python -m ragapp retrieve "질문" --top-n 50 --rerank --top-k 8
    """
    from ragapp.rerankers.llm_reranker import LLMReranker
    from ragapp.rerankers.base import NoOpReranker
    
    # Load config and use defaults if not specified
    config = get_config()
    
    # Determine retriever mode
    if mode is None:
        mode = config.retriever_mode  # Use from config
    
    if top_n is None:
        top_n = config.top_k  # Use TOP_K from config for initial retrieval
    
    if top_k is None:
        top_k = config.rerank_top_k  # Use RERANK_TOP_K from config
    
    # Build panel text based on mode
    if mode == "elastic":
        panel_text = (
            f"[bold cyan]Query:[/bold cyan] {query}\n"
            f"[bold cyan]Mode:[/bold cyan] Elasticsearch\n"
            f"[bold cyan]Index:[/bold cyan] {config.elastic_index_name}\n"
            f"[bold cyan]Top N (initial):[/bold cyan] {top_n}\n"
            f"[bold cyan]Rerank:[/bold cyan] {rerank}"
        )
    else:
        panel_text = (
            f"[bold cyan]Query:[/bold cyan] {query}\n"
            f"[bold cyan]Mode:[/bold cyan] Local (BM25+FAISS)\n"
            f"[bold cyan]Index:[/bold cyan] {index_dir}\n"
            f"[bold cyan]Top N (initial):[/bold cyan] {top_n}\n"
            f"[bold cyan]Rerank:[/bold cyan] {rerank}"
        )
    
    if rerank:
        panel_text += f"\n[bold cyan]Top K (final):[/bold cyan] {top_k}"
    
    console.print(Panel.fit(panel_text, title="🔍 Hybrid Search"))
    
    try:
        # Initialize retriever based on mode
        if mode == "elastic":
            from ragapp.retrievers.elastic_retriever import ElasticHybridRetriever
            
            with console.status("[bold green]Connecting to Elasticsearch..."):
                retriever = ElasticHybridRetriever(
                    host=config.elastic_host,
                    port=config.elastic_port,
                    index_name=config.elastic_index_name,
                    embedding_model=config.local_embedding_model
                )
                
                if not retriever.index_exists():
                    console.print(f"[bold red]Error:[/bold red] Elasticsearch index '{config.elastic_index_name}' not found")
                    console.print("Run 'python -m ragapp index-elastic' first")
                    raise typer.Exit(1)
        else:
            from ragapp.retrievers.local_hybrid import LocalHybridRetriever
            
            index_path = Path(index_dir)
            
            if not index_path.exists():
                console.print(f"[bold red]Error:[/bold red] Index not found: {index_dir}")
                console.print("Run 'python -m ragapp index' first to build the index.")
                raise typer.Exit(1)
            
            with console.status("[bold green]Loading index..."):
                retriever = LocalHybridRetriever(index_path)
        
        # Retrieve
        with console.status("[bold green]Searching..."):
            results = retriever.retrieve(query, top_k=top_n)
        
        # Rerank if enabled
        if rerank:
            try:
                console.print(f"\n[bold yellow]🔄 Reranking with LLM...[/bold yellow]")
                reranker = LLMReranker()
                
                with console.status(f"[bold green]Reranking {len(results)} → {top_k} documents..."):
                    results = reranker.rerank(query, results, top_k=top_k)
                
                console.print(f"[bold green]✅ Reranked to top {len(results)}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Reranking failed:[/bold red] {e}")
                console.print(f"[yellow]Continuing with original results...[/yellow]")
                # Fallback to no-op reranker
                results = results[:top_k]
        
        # Save to file if requested
        if output:
            import json
            output_data = {
                "query": query,
                "top_n": top_n,
                "results": [
                    {
                        "rank": i,
                        "score": doc.score,
                        "doc_id": doc.metadata.get('doc_id', 'N/A'),
                        "chunk_id": doc.metadata.get('chunk_id', 'N/A'),
                        "content": doc.content,
                        "metadata": doc.metadata
                    }
                    for i, doc in enumerate(results, 1)
                ]
            }
            
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            console.print(f"\n[bold green]✅ Results saved to:[/bold green] {output}")
        
        # Display results (simple format for better Korean support)
        console.print(f"\n[bold green]📄 Retrieved {len(results)} documents:[/bold green]\n")
        
        for i, doc in enumerate(results, 1):
            content_preview = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            doc_id = doc.metadata.get('doc_id', 'N/A')
            
            # Truncate long doc_id for better display
            if len(doc_id) > 60:
                doc_id_display = doc_id[:57] + "..."
            else:
                doc_id_display = doc_id
            
            # Show both original and rerank scores if available
            score_display = f"Score: {doc.score:.4f}"
            if 'rerank_score' in doc.metadata:
                orig_score = doc.metadata.get('original_score', 0.0)
                score_display = f"Rerank: {doc.score:.4f} (orig: {orig_score:.4f})"
            
            console.print(f"\n[bold cyan]#{i}[/bold cyan] [dim]({score_display})[/dim]")
            console.print(f"[yellow]Doc:[/yellow] {doc_id_display}")
            console.print(f"{content_preview}")
            console.print("─" * 80)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def health():
    """
    Check health status of external services (Elasticsearch, vLLM)
    
    Example:
        docker compose --profile local run --rm app python -m ragapp health
        docker compose --profile server run --rm app python -m ragapp health
    """
    import httpx
    from elasticsearch import Elasticsearch
    
    config = get_config()
    all_healthy = True
    
    console.print("\n[bold cyan]🏥 Health Check[/bold cyan]\n")
    
    # Check Elasticsearch (if server mode or retriever is elastic)
    if config.is_server_mode or config.retriever_mode == "elastic":
        try:
            es = Elasticsearch(
                [f"http://{config.elastic_host}:{config.elastic_port}"],
                request_timeout=5
            )
            if es.ping():
                console.print("[bold green]✅ Elasticsearch[/bold green] - Connected")
                # Get cluster info
                info = es.info()
                version = info.get('version', {}).get('number', 'unknown')
                console.print(f"   Version: {version}")
            else:
                console.print("[bold red]❌ Elasticsearch[/bold red] - Ping failed")
                all_healthy = False
        except Exception as e:
            console.print(f"[bold red]❌ Elasticsearch[/bold red] - Connection failed: {e}")
            all_healthy = False
    else:
        console.print("[dim]⏭️  Elasticsearch[/dim] - Skipped (local mode)")
    
    # Check vLLM (if server_http provider and SERVER_LLM_BASE_URL is set)
    if config.llm_provider == "server_http" and config.server_llm_base_url:
        try:
            base_url = config.server_llm_base_url.rstrip('/')
            models_url = f"{base_url}/v1/models"
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(models_url)
                response.raise_for_status()
                
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    model_id = data["data"][0].get("id", "unknown")
                    console.print(f"[bold green]✅ vLLM[/bold green] - Connected")
                    console.print(f"   Model: {model_id}")
                    console.print(f"   Endpoint: {base_url}")
                else:
                    console.print("[bold yellow]⚠️  vLLM[/bold yellow] - Connected but no models found")
                    all_healthy = False
        except httpx.TimeoutException:
            console.print(f"[bold red]❌ vLLM[/bold red] - Timeout (endpoint: {config.server_llm_base_url})")
            all_healthy = False
        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]❌ vLLM[/bold red] - HTTP {e.response.status_code} (endpoint: {config.server_llm_base_url})")
            all_healthy = False
        except Exception as e:
            console.print(f"[bold red]❌ vLLM[/bold red] - Connection failed: {e}")
            all_healthy = False
    elif config.llm_provider == "local_api":
        console.print("[dim]⏭️  vLLM[/dim] - Skipped (using local_api)")
    else:
        console.print("[dim]⏭️  vLLM[/dim] - Skipped (SERVER_LLM_BASE_URL not set)")
    
    console.print()
    if all_healthy:
        console.print("[bold green]✅ All services are healthy[/bold green]")
        raise typer.Exit(0)
    else:
        console.print("[bold red]❌ Some services are unhealthy[/bold red]")
        raise typer.Exit(1)


@app.command()
def version():
    """
    Display version information
    """
    from ragapp import __version__
    console.print(f"[bold cyan]RAG App[/bold cyan] version [bold green]{__version__}[/bold green]")


def setup_logging():
    """Setup loguru logger"""
    try:
        config = get_config()
        log_level = config.log_level
    except Exception:
        log_level = "INFO"
    
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level
    )


if __name__ == "__main__":
    setup_logging()
    app()
