"""Output formatters for PDF analysis results using rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pdf_analyzer.analyzer import CollectionStats, DocumentInfo, PageAnalysis, TableInfo


def format_document_info(doc_info: DocumentInfo, console: Console) -> None:
    """Print document information to console.

    Args:
        doc_info: Document information to display.
        console: Rich console for output.
    """
    # Document header
    console.print(
        Panel(
            f"[bold]{doc_info.file_path.name}[/bold]",
            title="PDF Document Info",
            border_style="blue",
        )
    )

    # Basic info table
    basic_table = Table(show_header=False, box=None, padding=(0, 2))
    basic_table.add_column("Property", style="cyan")
    basic_table.add_column("Value")

    basic_table.add_row("File", str(doc_info.file_path))
    basic_table.add_row("Size", doc_info.file_size_readable)
    basic_table.add_row("Pages", str(doc_info.page_count))

    console.print(basic_table)
    console.print()

    # Metadata section
    meta = doc_info.metadata
    has_metadata = any([
        meta.title, meta.author, meta.creator,
        meta.creation_date, meta.mod_date
    ])

    if has_metadata:
        console.print("[bold cyan]Metadata[/bold cyan]")
        meta_table = Table(show_header=False, box=None, padding=(0, 2))
        meta_table.add_column("Field", style="dim")
        meta_table.add_column("Value")

        if meta.title:
            meta_table.add_row("Title", meta.title)
        if meta.author:
            meta_table.add_row("Author", meta.author)
        if meta.subject:
            meta_table.add_row("Subject", meta.subject)
        if meta.creator:
            meta_table.add_row("Creator", meta.creator)
        if meta.producer:
            meta_table.add_row("Producer", meta.producer)
        if meta.creation_date:
            meta_table.add_row("Created", meta.creation_date)
        if meta.mod_date:
            meta_table.add_row("Modified", meta.mod_date)

        console.print(meta_table)
        console.print()

    # Page summary table
    console.print("[bold cyan]Page Summary[/bold cyan]")
    page_table = Table(box=None)
    page_table.add_column("Page", justify="right", style="bold")
    page_table.add_column("Size (pt)", justify="right")
    page_table.add_column("Text Blocks", justify="right")
    page_table.add_column("Images", justify="right")

    total_text_blocks = 0
    total_images = 0

    for summary in doc_info.page_summaries:
        page_table.add_row(
            str(summary["page_number"]),
            f"{summary['width']:.0f} x {summary['height']:.0f}",
            str(summary.get("text_block_count", 0)),
            str(summary.get("image_count", 0)),
        )
        total_text_blocks += summary.get("text_block_count", 0)
        total_images += summary.get("image_count", 0)

    # Total row
    page_table.add_row(
        "[bold]Total[/bold]",
        "",
        f"[bold]{total_text_blocks:,}[/bold]",
        f"[bold]{total_images:,}[/bold]",
    )

    console.print(page_table)


def format_page_analysis(
    analysis: PageAnalysis,
    console: Console,
    element: str | None = None,
    limit: int = 20,
) -> None:
    """Print page analysis to console.

    Args:
        analysis: Page analysis to display.
        console: Rich console for output.
        element: Specific element to show (text, images).
                 If None, shows summary of all elements.
        limit: Maximum number of items to display.
    """
    # Page header
    console.print(
        Panel(
            f"[bold]Page {analysis.page_number}[/bold] - "
            f"{analysis.width:.0f} x {analysis.height:.0f} pt",
            title="Page Analysis",
            border_style="blue",
        )
    )

    if element is None:
        # Show summary of all elements
        _format_page_summary(analysis, console)
    elif element == "text":
        _format_text_blocks(analysis, console, limit)
    elif element == "images":
        _format_images(analysis, console, limit)
    else:
        console.print(f"[red]Unknown element type: {element}[/red]")


def _format_page_summary(analysis: PageAnalysis, console: Console) -> None:
    """Format page summary with element counts."""
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Element", style="cyan")
    summary_table.add_column("Count", justify="right")

    summary_table.add_row("Text Blocks", f"{analysis.text_block_count:,}")
    summary_table.add_row("  (Est. words)", f"~{analysis.word_count:,}")
    summary_table.add_row("  (Total chars)", f"~{analysis.total_text_length:,}")
    summary_table.add_row("Images", f"{analysis.image_count:,}")

    console.print(summary_table)


def _format_text_blocks(
    analysis: PageAnalysis,
    console: Console,
    limit: int,
) -> None:
    """Format text block details."""
    console.print(f"[bold cyan]Text Blocks[/bold cyan] (showing first {limit})")
    console.print()

    if not analysis.text_blocks:
        console.print("[dim]No text blocks found on this page.[/dim]")
        return

    text_table = Table(box=None)
    text_table.add_column("#", justify="right", style="dim")
    text_table.add_column("Label", style="cyan")
    text_table.add_column("X0", justify="right")
    text_table.add_column("Top", justify="right")
    text_table.add_column("Width", justify="right")
    text_table.add_column("Height", justify="right")
    text_table.add_column("Text Preview", max_width=40, overflow="ellipsis")

    for i, block in enumerate(analysis.text_blocks[:limit], 1):
        # Truncate text preview
        preview = block.text[:50].replace("\n", " ")
        if len(block.text) > 50:
            preview += "..."

        text_table.add_row(
            str(i),
            block.label,
            f"{block.bbox.x0:.1f}",
            f"{block.bbox.top:.1f}",
            f"{block.bbox.width:.1f}",
            f"{block.bbox.height:.1f}",
            preview,
        )

    console.print(text_table)

    if len(analysis.text_blocks) > limit:
        console.print(
            f"\n[dim]... and {len(analysis.text_blocks) - limit} more text blocks[/dim]"
        )

    # Label distribution
    console.print()
    console.print("[bold cyan]Label Distribution[/bold cyan]")
    label_counts: dict[str, int] = {}
    for block in analysis.text_blocks:
        label_counts[block.label] = label_counts.get(block.label, 0) + 1

    label_table = Table(box=None)
    label_table.add_column("Label")
    label_table.add_column("Count", justify="right")
    label_table.add_column("Percentage", justify="right")

    total = len(analysis.text_blocks)
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        pct = (count / total) * 100 if total > 0 else 0
        label_table.add_row(label, f"{count:,}", f"{pct:.1f}%")

    console.print(label_table)


def _format_images(
    analysis: PageAnalysis,
    console: Console,
    limit: int,
) -> None:
    """Format image details."""
    console.print("[bold cyan]Images[/bold cyan]")
    console.print()

    if not analysis.images:
        console.print("[dim]No images found on this page.[/dim]")
        return

    img_table = Table(box=None)
    img_table.add_column("#", justify="right", style="dim")
    img_table.add_column("X0", justify="right")
    img_table.add_column("Top", justify="right")
    img_table.add_column("Width", justify="right")
    img_table.add_column("Height", justify="right")
    img_table.add_column("Caption", style="dim", max_width=30, overflow="ellipsis")

    for i, img in enumerate(analysis.images[:limit], 1):
        img_table.add_row(
            str(i),
            f"{img.x0:.1f}",
            f"{img.top:.1f}",
            f"{img.width:.1f}",
            f"{img.height:.1f}",
            img.caption or "-",
        )

    console.print(img_table)

    if len(analysis.images) > limit:
        console.print(
            f"\n[dim]... and {len(analysis.images) - limit} more images[/dim]"
        )


def format_tables(
    tables: list[TableInfo],
    console: Console,
    show_content: bool = True,
    max_col_width: int = 15,
) -> None:
    """Print detected tables to console.

    Args:
        tables: List of TableInfo objects.
        console: Rich console for output.
        show_content: Whether to show table cell contents.
        max_col_width: Maximum column width for cell display.
    """
    if not tables:
        console.print(
            Panel(
                "[dim]No tables detected in this document.[/dim]",
                title="Tables",
                border_style="blue",
            )
        )
        return

    # Group tables by page
    tables_by_page: dict[int, list[TableInfo]] = {}
    for table in tables:
        if table.page_number not in tables_by_page:
            tables_by_page[table.page_number] = []
        tables_by_page[table.page_number].append(table)

    # Summary header
    total_tables = len(tables)
    pages_with_tables = len(tables_by_page)
    console.print(
        Panel(
            f"[bold]{total_tables} table(s)[/bold] found on {pages_with_tables} page(s)",
            title="Tables Detected",
            border_style="blue",
        )
    )

    # Display each table
    for page_num in sorted(tables_by_page.keys()):
        page_tables = tables_by_page[page_num]
        console.print(f"\n[bold cyan]Page {page_num}[/bold cyan]: {len(page_tables)} table(s)")

        for table in page_tables:
            _format_single_table(table, console, show_content, max_col_width)


def _format_single_table(
    table: TableInfo,
    console: Console,
    show_content: bool,
    max_col_width: int,
) -> None:
    """Format a single table."""
    console.print()
    console.print(
        f"[bold]Table {table.table_index + 1}[/bold] "
        f"({table.row_count} rows x {table.col_count} cols)"
    )
    console.print(
        f"[dim]Location: ({table.x0:.1f}, {table.top:.1f}) - "
        f"({table.x1:.1f}, {table.bottom:.1f}) | "
        f"Size: {table.width:.1f} x {table.height:.1f} pt[/dim]"
    )

    if not show_content or not table.cells:
        return

    # Create rich table for display
    rich_table = Table(show_header=False, box=None, padding=(0, 1))

    # Add columns
    for _ in range(table.col_count):
        rich_table.add_column(max_width=max_col_width, overflow="ellipsis")

    # Add rows
    for row_idx, row in enumerate(table.cells):
        formatted_cells = []
        for cell in row:
            cell_text = _truncate_cell(cell, max_col_width)
            # Bold first row (likely header)
            if row_idx == 0:
                cell_text = f"[bold]{cell_text}[/bold]"
            formatted_cells.append(cell_text)
        rich_table.add_row(*formatted_cells)

    console.print(rich_table)


def _truncate_cell(cell: str | None, max_width: int) -> str:
    """Truncate cell content for display."""
    if cell is None:
        return "[dim]-[/dim]"

    # Convert to string if needed
    cell_str = str(cell)

    # Clean up whitespace
    cell_str = " ".join(cell_str.split())

    if len(cell_str) <= max_width:
        return cell_str

    return cell_str[: max_width - 2] + ".."


def format_table_summary(
    table_summary: dict[int, int],
    console: Console,
    total_pages: int,
) -> None:
    """Print table summary per page.

    Args:
        table_summary: Dictionary mapping page number to table count.
        console: Rich console for output.
        total_pages: Total number of pages in document.
    """
    console.print(
        Panel(
            f"[bold]{sum(table_summary.values())} table(s)[/bold] "
            f"on {len(table_summary)} of {total_pages} pages",
            title="Table Summary",
            border_style="blue",
        )
    )

    if not table_summary:
        console.print("[dim]No tables detected.[/dim]")
        return

    summary_table = Table(box=None)
    summary_table.add_column("Page", justify="right", style="bold")
    summary_table.add_column("Tables", justify="right")

    for page_num in sorted(table_summary.keys()):
        summary_table.add_row(str(page_num), str(table_summary[page_num]))

    console.print(summary_table)


def format_collection_stats(stats: CollectionStats, console: Console) -> None:
    """Print collection statistics to console.

    Args:
        stats: Collection statistics to display.
        console: Rich console for output.
    """
    # Header
    console.print(
        Panel(
            f"[bold]{stats.file_count} file(s)[/bold] analyzed, "
            f"[bold]{stats.total_pages}[/bold] total pages",
            title="PDF Collection Statistics",
            border_style="blue",
        )
    )

    if stats.file_count == 0:
        console.print("[dim]No files were successfully analyzed.[/dim]")
        if stats.errors:
            _format_errors(stats.errors, console)
        return

    # Page size distribution
    console.print("\n[bold cyan]Page Size Distribution[/bold cyan]")
    size_table = Table(box=None)
    size_table.add_column("Size", style="dim")
    size_table.add_column("Count", justify="right")
    size_table.add_column("Percentage", justify="right")

    total_pages = sum(stats.page_size_distribution.values())
    for size_name, count in sorted(
        stats.page_size_distribution.items(),
        key=lambda x: -x[1]
    ):
        pct = (count / total_pages * 100) if total_pages > 0 else 0
        size_table.add_row(size_name, str(count), f"{pct:.1f}%")

    console.print(size_table)

    # Content statistics
    console.print("\n[bold cyan]Content Statistics (per page)[/bold cyan]")
    content_table = Table(box=None)
    content_table.add_column("Metric", style="dim")
    content_table.add_column("Min", justify="right")
    content_table.add_column("Max", justify="right")
    content_table.add_column("Avg", justify="right")
    content_table.add_column("Median", justify="right")

    content_table.add_row(
        "Text Blocks",
        f"{stats.text_blocks_stats['min']:.0f}",
        f"{stats.text_blocks_stats['max']:.0f}",
        f"{stats.text_blocks_stats['avg']:.0f}",
        f"{stats.text_blocks_stats['median']:.0f}",
    )
    content_table.add_row(
        "Images",
        f"{stats.images_stats['min']:.1f}",
        f"{stats.images_stats['max']:.1f}",
        f"{stats.images_stats['avg']:.1f}",
        f"{stats.images_stats['median']:.1f}",
    )
    content_table.add_row(
        "Tables (per file)",
        f"{stats.tables_stats['min']:.0f}",
        f"{stats.tables_stats['max']:.0f}",
        f"{stats.tables_stats['avg']:.1f}",
        f"{stats.tables_stats['median']:.0f}",
    )

    console.print(content_table)

    # Errors
    if stats.errors:
        _format_errors(stats.errors, console)


def _format_errors(errors: list[tuple], console: Console) -> None:
    """Format error list."""
    console.print(f"\n[bold red]Errors ({len(errors)} files)[/bold red]")
    for path, error in errors[:10]:
        console.print(f"  [dim]{path.name}:[/dim] {error}")
    if len(errors) > 10:
        console.print(f"  [dim]... and {len(errors) - 10} more[/dim]")
