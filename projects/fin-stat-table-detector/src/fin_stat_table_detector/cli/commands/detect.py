"""Detect command for financial statement table detection.

Processes PDF files and exports detection results to Label Studio format.
Uses img2table and docling detectors to maximize recall.
"""

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import click
from pypdf import PdfReader
from rich.console import Console, Group
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from fin_stat_table_detector.detectors import DoclingDetector
from fin_stat_table_detector.ensemble import EnsembleDetector
from fin_stat_table_detector.exporters import LabelStudioExporter, PageDimensions

console = Console()


def create_detectors() -> list:
    """Create detector instances.

    Docling: ML 기반 테이블 감지 (borderless 표 포함)

    Returns:
        List of detector instances.
    """
    return [
        DoclingDetector(),
    ]


def find_pdf_files(path: Path) -> list[Path]:
    """Find PDF files in the given path.

    Args:
        path: File or directory path.

    Returns:
        List of PDF file paths.
    """
    if path.is_file():
        if path.suffix.lower() == ".pdf":
            return [path]
        return []

    pdf_files = list(path.glob("**/*.pdf"))
    return sorted(pdf_files)


def get_pdf_page_info(pdf_path: Path) -> list[tuple[float, float]]:
    """Get page dimensions from PDF using pypdf.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        List of (width, height) tuples for each page.
    """
    reader = PdfReader(pdf_path)
    page_dims = []
    for page in reader.pages:
        media_box = page.mediabox
        page_dims.append((float(media_box.width), float(media_box.height)))
    return page_dims


def convert_pdf_to_images(
    pdf_path: Path,
    images_dir: Path,
    dpi: int = 150,
) -> list[tuple[int, Path, PageDimensions]]:
    """Convert PDF pages to images.

    Args:
        pdf_path: Path to the PDF file.
        images_dir: Directory to save images.
        dpi: Image resolution (dots per inch).

    Returns:
        List of tuples: (page_number, image_path, page_dimensions).
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise click.ClickException(
            "pdf2image is required for image conversion. Install with: uv add pdf2image"
        )

    images_dir.mkdir(parents=True, exist_ok=True)
    pdf_stem = pdf_path.stem

    # Get PDF page dimensions using pypdf
    page_dims_list = get_pdf_page_info(pdf_path)

    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=dpi)

    results = []
    for i, (image, (pdf_width, pdf_height)) in enumerate(
        zip(images, page_dims_list), start=1
    ):
        image_filename = f"{pdf_stem}_page_{i:03d}.jpg"
        image_path = images_dir / image_filename
        image.save(image_path, "JPEG", quality=95)

        dims = PageDimensions(
            pdf_width=pdf_width,
            pdf_height=pdf_height,
            image_width=image.width,
            image_height=image.height,
        )
        results.append((i, image_path, dims))

    return results


def process_pdf_worker(
    pdf_path_str: str,
    images_dir_str: str,
    dpi: int,
    summary_only: bool,
) -> dict:
    """Worker function for parallel PDF processing.

    This is a standalone function that can be pickled for multiprocessing.
    It creates its own detector instance.

    Args:
        pdf_path_str: Path to the PDF file (as string for pickling).
        images_dir_str: Directory to save images (as string for pickling).
        dpi: Image resolution.
        summary_only: If True, don't generate images.

    Returns:
        Dictionary with processing statistics.
    """
    pdf_path = Path(pdf_path_str)
    images_dir = Path(images_dir_str)

    # Create detector in worker process
    detector_instances = create_detectors()
    ensemble = EnsembleDetector(detector_instances)

    stats = {
        "pdf_path": str(pdf_path),
        "pages": 0,
        "tables_detected": 0,
        "categories": {},
        "tables": [],  # Store table data for later export
    }

    try:
        # Detect financial tables
        tables = ensemble.detect_financial_tables(str(pdf_path))
        stats["tables_detected"] = len(tables)
        stats["tables"] = tables

        # Count by category
        for table in tables:
            cat = table.category
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

        if summary_only:
            reader = PdfReader(pdf_path)
            stats["pages"] = len(reader.pages)
        else:
            page_results = convert_pdf_to_images(pdf_path, images_dir, dpi)
            stats["pages"] = len(page_results)
            stats["page_results"] = [
                (pn, str(ip), dims) for pn, ip, dims in page_results
            ]

    except Exception as e:
        stats["error"] = str(e)

    return stats


def process_pdf(
    pdf_path: Path,
    detector: EnsembleDetector,
    exporter: LabelStudioExporter,
    images_dir: Path,
    dpi: int,
    summary_only: bool,
) -> dict:
    """Process a single PDF file.

    Args:
        pdf_path: Path to the PDF file.
        detector: EnsembleDetector instance.
        exporter: LabelStudioExporter instance.
        images_dir: Directory to save images.
        dpi: Image resolution.
        summary_only: If True, don't generate images.

    Returns:
        Dictionary with processing statistics.
    """
    stats = {
        "pdf_path": str(pdf_path),
        "pages": 0,
        "tables_detected": 0,
        "categories": {},
    }

    # Detect financial tables
    tables = detector.detect_financial_tables(str(pdf_path))
    stats["tables_detected"] = len(tables)

    # Count by category
    for table in tables:
        cat = table.category
        stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

    if summary_only:
        # Just count pages without image conversion
        reader = PdfReader(pdf_path)
        stats["pages"] = len(reader.pages)
        return stats

    # Convert PDF to images and add to exporter
    page_results = convert_pdf_to_images(pdf_path, images_dir, dpi)
    stats["pages"] = len(page_results)

    # Group tables by page
    tables_by_page: dict[int, list] = {}
    for table in tables:
        tables_by_page.setdefault(table.page, []).append(table)

    # Add each page to exporter
    for page_num, image_path, dims in page_results:
        page_tables = tables_by_page.get(page_num, [])
        exporter.add_page_results(str(image_path), page_tables, dims)

    return stats


def process_sequential(
    pdf_files: list[Path],
    images_dir: Path,
    dpi: int,
    summary_only: bool,
    exporter: LabelStudioExporter,
) -> list[dict]:
    """Process PDF files sequentially with spinner progress.

    Args:
        pdf_files: List of PDF file paths.
        images_dir: Directory to save images.
        dpi: Image resolution.
        summary_only: If True, don't generate images.
        exporter: LabelStudioExporter instance.

    Returns:
        List of statistics dictionaries.
    """
    from rich.progress import Progress, SpinnerColumn, TextColumn

    detector_instances = create_detectors()
    ensemble = EnsembleDetector(detector_instances)

    console.print(
        f"[dim]Using detectors: {', '.join(d.name for d in detector_instances)}[/dim]\n"
    )

    all_stats = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing PDFs...", total=len(pdf_files))

        for pdf_path in pdf_files:
            progress.update(task, description=f"Processing {pdf_path.name}...")
            try:
                stats = process_pdf(
                    pdf_path,
                    ensemble,
                    exporter,
                    images_dir,
                    dpi,
                    summary_only,
                )
                all_stats.append(stats)
            except Exception as e:
                console.print(f"[red]Error processing {pdf_path}: {e}[/red]")
                all_stats.append(
                    {
                        "pdf_path": str(pdf_path),
                        "error": str(e),
                    }
                )
            progress.advance(task)

    return all_stats


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
                line.append("✗ ", style="red")
                line.append(name, style="red")
                line.append(f" (Error: {stats['error'][:30]}...)", style="dim red")
            else:
                pages = stats.get("pages", 0)
                tables = stats.get("tables_detected", 0)
                line = Text()
                line.append("✓ ", style="green")
                line.append(name, style="green")
                line.append(f" ({pages} pages, {tables} tables)", style="dim")
            lines.append(line)
        elif path_str in in_progress:
            # In progress
            line = Text()
            line.append("◐ ", style="yellow")
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


def process_parallel(
    pdf_files: list[Path],
    images_dir: Path,
    dpi: int,
    summary_only: bool,
    workers: int | None,
) -> list[dict]:
    """Process PDF files in parallel with live progress display.

    Args:
        pdf_files: List of PDF file paths.
        images_dir: Directory to save images.
        dpi: Image resolution.
        summary_only: If True, don't generate images.
        workers: Number of worker processes.

    Returns:
        List of statistics dictionaries.
    """
    num_workers = workers or os.cpu_count() or 4

    console.print(f"[dim]Using detectors: docling[/dim]")
    console.print(f"[dim]Workers: {num_workers}[/dim]\n")

    completed: dict[str, dict] = {}
    in_progress: set[str] = set()
    all_stats: list[dict] = []

    # Map future to pdf_path
    future_to_path: dict = {}

    with Live(
        build_progress_display(pdf_files, completed, in_progress, num_workers),
        console=console,
        refresh_per_second=4,
    ) as live:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            for pdf_path in pdf_files:
                future = executor.submit(
                    process_pdf_worker,
                    str(pdf_path),
                    str(images_dir),
                    dpi,
                    summary_only,
                )
                future_to_path[future] = pdf_path
                in_progress.add(str(pdf_path))
                live.update(
                    build_progress_display(
                        pdf_files, completed, in_progress, num_workers
                    )
                )

            # Process completed tasks
            for future in as_completed(future_to_path):
                pdf_path = future_to_path[future]
                path_str = str(pdf_path)

                try:
                    stats = future.result()
                except Exception as e:
                    stats = {"pdf_path": path_str, "error": str(e)}

                in_progress.discard(path_str)
                completed[path_str] = stats
                all_stats.append(stats)

                live.update(
                    build_progress_display(
                        pdf_files, completed, in_progress, num_workers
                    )
                )

    return all_stats


@click.command()
@click.argument(
    "input_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output JSON path. Default: <input>_labels.json",
)
@click.option(
    "--images-dir",
    "-i",
    type=click.Path(path_type=Path),
    default=Path("./images"),
    help="Directory to save page images. Default: ./images/",
)
@click.option(
    "--dpi",
    type=int,
    default=150,
    help="Image resolution (DPI). Default: 150",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show files to process without processing.",
)
@click.option(
    "--summary-only",
    "-s",
    is_flag=True,
    help="Show detection summary without generating images.",
)
@click.option(
    "--parallel",
    "-p",
    is_flag=True,
    help="Enable parallel processing for multiple files.",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=None,
    help="Number of worker processes. Default: CPU count.",
)
@click.option(
    "--dataset-name",
    "-d",
    type=str,
    default=None,
    help="Dataset name for Label Studio local file paths. "
    "Images will be referenced as /data/local-files/?d=<dataset-name>/<filename>",
)
def detect(
    input_path: Path,
    output: Path | None,
    images_dir: Path,
    dpi: int,
    dry_run: bool,
    summary_only: bool,
    parallel: bool,
    workers: int | None,
    dataset_name: str | None,
) -> None:
    """Detect financial tables in PDF files.

    Uses docling ML-based detector with OCR support.

    INPUT_PATH can be a single PDF file or a directory containing PDF files.

    Examples:

        fin-stat-table-detector detect report.pdf

        fin-stat-table-detector detect ./data/ --dry-run

        fin-stat-table-detector detect report.pdf --summary-only

        fin-stat-table-detector detect ./data/ --parallel --workers 4

        fin-stat-table-detector detect report.pdf -d samsung_2024
    """
    # Find PDF files
    pdf_files = find_pdf_files(input_path)

    if not pdf_files:
        console.print("[yellow]No PDF files found.[/yellow]")
        return

    # Dry run: just list files
    if dry_run:
        console.print(f"\n[bold]Files to process ({len(pdf_files)}):[/bold]\n")
        for pdf_path in pdf_files:
            console.print(f"  {pdf_path}")
        return

    # Determine output path
    if output is None:
        if input_path.is_file():
            output = input_path.with_suffix(".json").with_name(
                f"{input_path.stem}_labels.json"
            )
        else:
            output = input_path / "labels.json"

    # Create exporter
    exporter = LabelStudioExporter(dataset_name=dataset_name)

    # Process files
    start_time = time.perf_counter()

    if parallel and len(pdf_files) > 1:
        # Parallel processing
        all_stats = process_parallel(
            pdf_files, images_dir, dpi, summary_only, workers
        )
    else:
        # Sequential processing
        all_stats = process_sequential(
            pdf_files, images_dir, dpi, summary_only, exporter
        )

    elapsed_time = time.perf_counter() - start_time

    # Save results (unless summary-only)
    if not summary_only:
        # For parallel processing, need to populate exporter from stats
        if parallel and len(pdf_files) > 1:
            for stats in all_stats:
                if "error" in stats or "page_results" not in stats:
                    continue
                tables = stats.get("tables", [])
                tables_by_page: dict[int, list] = {}
                for table in tables:
                    tables_by_page.setdefault(table.page, []).append(table)

                for page_num, image_path_str, dims in stats["page_results"]:
                    page_tables = tables_by_page.get(page_num, [])
                    exporter.add_page_results(image_path_str, page_tables, dims)

        exporter.save(output)
        console.print(f"\n[green]Results saved to: {output}[/green]")
        console.print(f"[green]Images saved to: {images_dir}[/green]")

    # Print summary
    print_summary(all_stats, elapsed_time)


def print_summary(all_stats: list[dict], elapsed_time: float) -> None:
    """Print processing summary.

    Args:
        all_stats: List of statistics dictionaries.
        elapsed_time: Total elapsed time in seconds.
    """
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
