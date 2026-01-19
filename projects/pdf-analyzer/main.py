"""PDF Analyzer CLI - Analyze PDF structure and elements."""

import sys
from pathlib import Path

import click
from rich.console import Console

from src.analyzer import PDFAnalyzer
from src.formatters import (
    format_document_info,
    format_page_analysis,
    format_table_summary,
    format_tables,
)

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
        uv run python main.py info sample.pdf
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
        uv run python main.py page sample.pdf
        uv run python main.py page sample.pdf --page 2
        uv run python main.py page sample.pdf -p 1 --element chars
        uv run python main.py page sample.pdf -p 1 -e lines --limit 50
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
        uv run python main.py tables sample.pdf
        uv run python main.py tables sample.pdf --page 3
        uv run python main.py tables sample.pdf --summary
        uv run python main.py tables sample.pdf --no-content
        uv run python main.py tables sample.pdf --col-width 20
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


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
