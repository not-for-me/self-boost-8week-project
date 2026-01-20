"""PDF Analyzer CLI - Analyze PDF structure and elements."""

import sys
from pathlib import Path

import click
from rich.console import Console

from pdf_analyzer.analyzer import PDFAnalyzer, analyze_collection
from pdf_analyzer.formatters import (
    format_collection_stats,
    format_document_info,
    format_page_analysis,
    format_table_summary,
    format_tables,
)
from pdf_analyzer.visualizer import create_simple_visual

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """PDF Analyzer - Understand PDF structure under the hood.

    This tool helps you analyze PDF files by extracting and displaying
    their internal elements: characters, lines, rectangles, and images.
    """
    pass


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, path_type=Path))
def info(pdf_file: Path):
    """Display document metadata and page summary.

    PDF_FILE: Path to the PDF file to analyze.

    Example:
        uv run pdf-analyzer info sample.pdf
    """
    try:
        analyzer = PDFAnalyzer(pdf_file)
        doc_info = analyzer.get_document_info()
        format_document_info(doc_info, console)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error analyzing PDF:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--page", "-p",
    type=int,
    default=1,
    help="Page number to analyze (1-indexed). Default: 1",
)
@click.option(
    "--element", "-e",
    type=click.Choice(["chars", "lines", "rects", "images"]),
    default=None,
    help="Specific element type to display. Default: show summary",
)
@click.option(
    "--limit", "-l",
    type=int,
    default=20,
    help="Maximum items to display. Default: 20",
)
def page(pdf_file: Path, page: int, element: str | None, limit: int):
    """Analyze a specific page in detail.

    PDF_FILE: Path to the PDF file to analyze.

    Examples:
        uv run pdf-analyzer page sample.pdf
        uv run pdf-analyzer page sample.pdf --page 2
        uv run pdf-analyzer page sample.pdf -p 1 --element chars
        uv run pdf-analyzer page sample.pdf -p 1 -e lines --limit 50
    """
    try:
        analyzer = PDFAnalyzer(pdf_file)
        analysis = analyzer.analyze_page(page)
        format_page_analysis(analysis, console, element=element, limit=limit)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error analyzing PDF:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--page", "-p",
    type=int,
    default=None,
    help="Specific page to analyze. Default: all pages",
)
@click.option(
    "--summary", "-s",
    is_flag=True,
    help="Show summary only (table count per page)",
)
@click.option(
    "--no-content",
    is_flag=True,
    help="Hide table cell contents",
)
@click.option(
    "--col-width", "-w",
    type=int,
    default=15,
    help="Maximum column width for display. Default: 15",
)
def tables(
    pdf_file: Path,
    page: int | None,
    summary: bool,
    no_content: bool,
    col_width: int,
):
    """Detect and display tables in PDF.

    PDF_FILE: Path to the PDF file to analyze.

    Examples:
        uv run pdf-analyzer tables sample.pdf
        uv run pdf-analyzer tables sample.pdf --page 3
        uv run pdf-analyzer tables sample.pdf --summary
        uv run pdf-analyzer tables sample.pdf --no-content
        uv run pdf-analyzer tables sample.pdf --col-width 20
    """
    try:
        analyzer = PDFAnalyzer(pdf_file)

        if summary:
            # Show summary only
            table_summary = analyzer.get_table_summary()
            doc_info = analyzer.get_document_info()
            format_table_summary(table_summary, console, doc_info.page_count)
        else:
            # Extract and display tables
            detected_tables = analyzer.extract_tables(page_number=page)
            format_tables(
                detected_tables,
                console,
                show_content=not no_content,
                max_col_width=col_width,
            )
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error analyzing PDF:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--page", "-p",
    type=int,
    default=1,
    help="Page number to visualize (1-indexed). Default: 1",
)
@click.option(
    "--width", "-w",
    type=int,
    default=60,
    help="Visualization width in characters. Default: 60",
)
@click.option(
    "--height", "-h",
    type=int,
    default=30,
    help="Visualization height in characters. Default: 30",
)
@click.option(
    "--with-tables", "-t",
    is_flag=True,
    help="Include table boundaries in visualization",
)
def visual(pdf_file: Path, page: int, width: int, height: int, with_tables: bool):
    """Visualize page layout using ASCII art.

    PDF_FILE: Path to the PDF file to visualize.

    Examples:
        uv run pdf-analyzer visual sample.pdf
        uv run pdf-analyzer visual sample.pdf --page 2
        uv run pdf-analyzer visual sample.pdf --width 80 --height 40
        uv run pdf-analyzer visual sample.pdf --with-tables
    """
    try:
        analyzer = PDFAnalyzer(pdf_file)
        analysis = analyzer.analyze_page(page)

        tables = None
        if with_tables:
            tables = analyzer.extract_tables(page_number=page)

        output = create_simple_visual(
            analysis,
            tables=tables,
            width=width,
            height=height,
        )
        console.print(output)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error visualizing PDF:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("pdf_files", nargs=-1, type=click.Path(path_type=Path))
@click.option(
    "--limit", "-l",
    type=int,
    default=None,
    help="Maximum number of files to analyze. Default: all",
)
def stats(pdf_files: tuple[Path, ...], limit: int | None):
    """Analyze multiple PDF files and show aggregated statistics.

    PDF_FILES: One or more PDF file paths (supports glob patterns in shell).

    Examples:
        uv run pdf-analyzer stats *.pdf
        uv run pdf-analyzer stats ../data/**/*.pdf
        uv run pdf-analyzer stats file1.pdf file2.pdf file3.pdf
        uv run pdf-analyzer stats ../data/**/*.pdf --limit 100
    """
    import glob as glob_module

    # Expand glob patterns and collect all PDF files
    all_files: list[Path] = []

    for pattern in pdf_files:
        pattern_str = str(pattern)
        # Check if it's a glob pattern
        if "*" in pattern_str or "?" in pattern_str:
            matches = glob_module.glob(pattern_str, recursive=True)
            all_files.extend(Path(m) for m in matches if m.endswith(".pdf"))
        elif pattern.exists() and pattern.suffix.lower() == ".pdf":
            all_files.append(pattern)

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in all_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(f)

    if not unique_files:
        console.print("[red]Error:[/red] No PDF files found.")
        sys.exit(1)

    # Apply limit
    if limit and limit < len(unique_files):
        unique_files = unique_files[:limit]
        console.print(f"[dim]Analyzing first {limit} of {len(all_files)} files[/dim]\n")

    # Progress callback
    def on_progress(current: int, total: int, file_path: Path) -> None:
        console.print(
            f"[dim][{current}/{total}] Analyzing {file_path.name}...[/dim]",
            end="\r",
        )

    try:
        collection_stats = analyze_collection(unique_files, on_progress=on_progress)
        console.print(" " * 80, end="\r")  # Clear progress line
        format_collection_stats(collection_stats, console)
    except Exception as e:
        console.print(f"\n[red]Error analyzing collection:[/red] {e}")
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
