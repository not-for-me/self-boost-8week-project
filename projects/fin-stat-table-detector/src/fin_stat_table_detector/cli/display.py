"""Display utilities for CLI output.

Provides functions for building progress displays and printing summaries.
"""

from pathlib import Path

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text


def build_progress_display(
    pdf_files: list[Path],
    completed: dict[str, dict],
    in_progress: set[str],
    num_workers: int,
) -> Group:
    """Build the progress display for parallel processing.

    Args:
        pdf_files: List of all PDF files.
        completed: Dict mapping pdf_path to stats for completed files.
        in_progress: Set of pdf_paths currently being processed.
        num_workers: Number of worker processes.

    Returns:
        Rich Group with progress display.
    """
    lines = []

    # Header
    done_count = len(completed)
    total_count = len(pdf_files)
    header = Text(f"Processing {total_count} files with {num_workers} workers...")
    header.stylize("bold")
    lines.append(header)
    lines.append(Text(""))

    for pdf_path in pdf_files:
        path_str = str(pdf_path)
        name = pdf_path.name

        if path_str in completed:
            # Completed
            stats = completed[path_str]
            if "error" in stats:
                line = Text()
                line.append("\u2717 ", style="red")
                line.append(name, style="red")
                line.append(f" (Error: {stats['error'][:30]}...)", style="dim red")
            else:
                pages = stats.get("pages", 0)
                tables = stats.get("tables_detected", 0)
                line = Text()
                line.append("\u2713 ", style="green")
                line.append(name, style="green")
                line.append(f" ({pages} pages, {tables} tables)", style="dim")
            lines.append(line)
        elif path_str in in_progress:
            # In progress
            line = Text()
            line.append("\u25d0 ", style="yellow")
            line.append(name, style="yellow")
            lines.append(line)
        else:
            # Pending
            line = Text()
            line.append("  ", style="dim")
            line.append(name, style="dim")
            lines.append(line)

    # Progress summary
    lines.append(Text(""))
    progress_text = Text(f"[{done_count}/{total_count}]", style="bold cyan")
    lines.append(progress_text)

    return Group(*lines)


def print_summary(
    all_stats: list[dict],
    elapsed_time: float,
    console: Console | None = None,
) -> None:
    """Print processing summary.

    Args:
        all_stats: List of statistics dictionaries.
        elapsed_time: Total elapsed time in seconds.
        console: Rich console for output. If None, creates a new one.
    """
    if console is None:
        console = Console()

    table = Table(title="\nDetection Summary")
    table.add_column("PDF", style="cyan")
    table.add_column("Pages", justify="right")
    table.add_column("Tables", justify="right")
    table.add_column("Categories", style="green")

    total_pages = 0
    total_tables = 0

    for stats in all_stats:
        if "error" in stats:
            table.add_row(
                Path(stats["pdf_path"]).name,
                "-",
                "-",
                f"[red]Error: {stats['error'][:30]}...[/red]",
            )
            continue

        pages = stats.get("pages", 0)
        tables = stats.get("tables_detected", 0)
        categories = stats.get("categories", {})

        total_pages += pages
        total_tables += tables

        cat_str = ", ".join(f"{k}:{v}" for k, v in categories.items()) or "-"

        table.add_row(
            Path(stats["pdf_path"]).name,
            str(pages),
            str(tables),
            cat_str,
        )

    # Add totals row
    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_pages}[/bold]",
        f"[bold]{total_tables}[/bold]",
        "",
    )

    console.print(table)
    console.print(f"\n[dim]Elapsed time: {elapsed_time:.2f}s[/dim]")
