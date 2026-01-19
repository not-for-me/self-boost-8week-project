"""Output formatters for PDF analysis results using rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.analyzer import CollectionStats, DocumentInfo, PageAnalysis, TableInfo


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
    page_table.add_column("Chars", justify="right")
    page_table.add_column("Lines", justify="right")
    page_table.add_column("Rects", justify="right")
    page_table.add_column("Images", justify="right")

    total_chars = 0
    total_lines = 0
    total_rects = 0
    total_images = 0

    for summary in doc_info.page_summaries:
        page_table.add_row(
            str(summary["page_number"]),
            f"{summary['width']:.0f} x {summary['height']:.0f}",
            str(summary["char_count"]),
            str(summary["line_count"]),
            str(summary["rect_count"]),
            str(summary["image_count"]),
        )
        total_chars += summary["char_count"]
        total_lines += summary["line_count"]
        total_rects += summary["rect_count"]
        total_images += summary["image_count"]

    # Total row
    page_table.add_row(
        "[bold]Total[/bold]",
        "",
        f"[bold]{total_chars:,}[/bold]",
        f"[bold]{total_lines:,}[/bold]",
        f"[bold]{total_rects:,}[/bold]",
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
        element: Specific element to show (chars, lines, rects, images).
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
    elif element == "chars":
        _format_chars(analysis, console, limit)
    elif element == "lines":
        _format_lines(analysis, console, limit)
    elif element == "rects":
        _format_rects(analysis, console, limit)
    elif element == "images":
        _format_images(analysis, console, limit)
    else:
        console.print(f"[red]Unknown element type: {element}[/red]")


def _format_page_summary(analysis: PageAnalysis, console: Console) -> None:
    """Format page summary with element counts."""
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Element", style="cyan")
    summary_table.add_column("Count", justify="right")

    summary_table.add_row("Characters", f"{analysis.char_count:,}")
    summary_table.add_row("  (Est. words)", f"~{analysis.word_count:,}")
    summary_table.add_row("Lines", f"{analysis.line_count:,}")
    summary_table.add_row("  Horizontal", f"{analysis.horizontal_lines:,}")
    summary_table.add_row("  Vertical", f"{analysis.vertical_lines:,}")
    summary_table.add_row("Rectangles", f"{analysis.rect_count:,}")
    summary_table.add_row("Images", f"{analysis.image_count:,}")

    console.print(summary_table)
    console.print()

    # Font usage
    fonts = analysis.get_font_usage()
    if fonts:
        console.print("[bold cyan]Font Usage[/bold cyan]")
        font_table = Table(box=None)
        font_table.add_column("Font", style="dim")
        font_table.add_column("Count", justify="right")
        font_table.add_column("Percentage", justify="right")

        total = sum(fonts.values())
        for font, count in list(fonts.items())[:10]:
            pct = (count / total) * 100 if total > 0 else 0
            font_table.add_row(font, f"{count:,}", f"{pct:.1f}%")

        console.print(font_table)


def _format_chars(
    analysis: PageAnalysis,
    console: Console,
    limit: int,
) -> None:
    """Format character details."""
    console.print(f"[bold cyan]Characters[/bold cyan] (showing first {limit})")
    console.print()

    if not analysis.chars:
        console.print("[dim]No characters found on this page.[/dim]")
        return

    char_table = Table(box=None)
    char_table.add_column("#", justify="right", style="dim")
    char_table.add_column("Char", justify="center")
    char_table.add_column("X0", justify="right")
    char_table.add_column("Top", justify="right")
    char_table.add_column("Font", style="dim")
    char_table.add_column("Size", justify="right")

    for i, char in enumerate(analysis.chars[:limit], 1):
        # Display character, escaping special chars
        display_char = repr(char.text) if char.text in ["\n", "\t", " "] else char.text
        char_table.add_row(
            str(i),
            display_char,
            f"{char.x0:.1f}",
            f"{char.top:.1f}",
            char.font_name or "-",
            f"{char.font_size:.1f}" if char.font_size else "-",
        )

    console.print(char_table)

    if len(analysis.chars) > limit:
        console.print(
            f"\n[dim]... and {len(analysis.chars) - limit} more characters[/dim]"
        )

    # Font summary
    console.print()
    fonts = analysis.get_font_usage()
    if fonts:
        console.print("[bold cyan]Font Summary[/bold cyan]")
        font_table = Table(box=None)
        font_table.add_column("Font")
        font_table.add_column("Count", justify="right")
        font_table.add_column("Percentage", justify="right")

        total = sum(fonts.values())
        for font, count in list(fonts.items())[:5]:
            pct = (count / total) * 100 if total > 0 else 0
            font_table.add_row(font, f"{count:,}", f"{pct:.1f}%")

        console.print(font_table)


def _format_lines(
    analysis: PageAnalysis,
    console: Console,
    limit: int,
) -> None:
    """Format line object details."""
    console.print(f"[bold cyan]Line Objects[/bold cyan] (showing first {limit})")
    console.print()

    if not analysis.lines:
        console.print("[dim]No line objects found on this page.[/dim]")
        return

    line_table = Table(box=None)
    line_table.add_column("#", justify="right", style="dim")
    line_table.add_column("X0", justify="right")
    line_table.add_column("Y0", justify="right")
    line_table.add_column("X1", justify="right")
    line_table.add_column("Y1", justify="right")
    line_table.add_column("Width", justify="right")
    line_table.add_column("Type", justify="center")

    for i, line in enumerate(analysis.lines[:limit], 1):
        line_type = "H" if line.is_horizontal else ("V" if line.is_vertical else "D")
        line_table.add_row(
            str(i),
            f"{line.x0:.1f}",
            f"{line.top:.1f}",
            f"{line.x1:.1f}",
            f"{line.bottom:.1f}",
            f"{line.width:.1f}" if line.width else "-",
            line_type,
        )

    console.print(line_table)
    console.print()

    # Line statistics
    console.print("[bold cyan]Line Statistics[/bold cyan]")
    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_column("Type", style="cyan")
    stats_table.add_column("Count", justify="right")

    stats_table.add_row("Horizontal", str(analysis.horizontal_lines))
    stats_table.add_row("Vertical", str(analysis.vertical_lines))
    diagonal = analysis.line_count - analysis.horizontal_lines - analysis.vertical_lines
    stats_table.add_row("Diagonal/Other", str(diagonal))
    stats_table.add_row("[bold]Total[/bold]", f"[bold]{analysis.line_count}[/bold]")

    console.print(stats_table)

    if len(analysis.lines) > limit:
        console.print(
            f"\n[dim]... and {len(analysis.lines) - limit} more lines[/dim]"
        )


def _format_rects(
    analysis: PageAnalysis,
    console: Console,
    limit: int,
) -> None:
    """Format rectangle details."""
    console.print(f"[bold cyan]Rectangles[/bold cyan] (showing first {limit})")
    console.print()

    if not analysis.rects:
        console.print("[dim]No rectangles found on this page.[/dim]")
        return

    rect_table = Table(box=None)
    rect_table.add_column("#", justify="right", style="dim")
    rect_table.add_column("X0", justify="right")
    rect_table.add_column("Top", justify="right")
    rect_table.add_column("Width", justify="right")
    rect_table.add_column("Height", justify="right")
    rect_table.add_column("Fill", justify="center")

    for i, rect in enumerate(analysis.rects[:limit], 1):
        has_fill = "Yes" if rect.fill_color else "No"
        rect_table.add_row(
            str(i),
            f"{rect.x0:.1f}",
            f"{rect.top:.1f}",
            f"{rect.width:.1f}",
            f"{rect.height:.1f}",
            has_fill,
        )

    console.print(rect_table)

    if len(analysis.rects) > limit:
        console.print(
            f"\n[dim]... and {len(analysis.rects) - limit} more rectangles[/dim]"
        )


def _format_images(
    analysis: PageAnalysis,
    console: Console,
    limit: int,
) -> None:
    """Format image details."""
    console.print(f"[bold cyan]Images[/bold cyan]")
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
    img_table.add_column("Name", style="dim")

    for i, img in enumerate(analysis.images[:limit], 1):
        img_table.add_row(
            str(i),
            f"{img.x0:.1f}",
            f"{img.top:.1f}",
            f"{img.width:.1f}",
            f"{img.height:.1f}",
            img.name or "-",
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

    # Clean up whitespace
    cell = " ".join(cell.split())

    if len(cell) <= max_width:
        return cell

    return cell[: max_width - 2] + ".."


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
        "Characters",
        f"{stats.chars_stats['min']:.0f}",
        f"{stats.chars_stats['max']:.0f}",
        f"{stats.chars_stats['avg']:.0f}",
        f"{stats.chars_stats['median']:.0f}",
    )
    content_table.add_row(
        "Lines",
        f"{stats.lines_stats['min']:.0f}",
        f"{stats.lines_stats['max']:.0f}",
        f"{stats.lines_stats['avg']:.0f}",
        f"{stats.lines_stats['median']:.0f}",
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

    # Font usage
    if stats.font_usage:
        console.print("\n[bold cyan]Font Usage (Top 10)[/bold cyan]")
        font_table = Table(box=None)
        font_table.add_column("Font", style="dim")
        font_table.add_column("Files", justify="right")
        font_table.add_column("Percentage", justify="right")

        for font, count in list(stats.font_usage.items())[:10]:
            pct = (count / stats.file_count * 100) if stats.file_count > 0 else 0
            font_table.add_row(font, str(count), f"{pct:.1f}%")

        console.print(font_table)

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
